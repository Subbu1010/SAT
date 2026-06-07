from datetime import datetime

import streamlit as st

from app.authentication.auth_service import AuthService
from app.database.supabase_client import get_supabase_admin_client
from app.services.admin_user_service import create_user, update_user
from app.services.admin_performance_service import (
    fetch_exam_history,
    fetch_student_performance_summary,
)
from app.services.login_history_service import fetch_login_history, login_history_schema_ready
from app.database.bulk_seed import reload_exam_catalog, seed_bulk_questions
from app.database.exam_catalog import EXAM_TYPES
from app.services.question_import_service import (
    QuestionImportService,
    apply_batch_label,
    payload_to_review_dataframe,
)
from app.services.import_progress import StreamlitImportProgress
from app.services.question_source import format_batch_name, normalize_source_name
from app.utils.datetime_display import CST
from app.services.question_service import QuestionService
from app.services.question_delete_service import delete_questions
from app.services.question_export_service import (
    backup_filename,
    cached_backup_count,
    cached_backup_package,
    cached_backup_sources,
    clear_backup_cache,
)
from app.services.question_template import (
    CSV_FILENAME,
    XLSX_FILENAME,
    build_template_csv_bytes,
    build_template_xlsx_bytes,
)
from app.utils.datetime_display import format_cst, format_rows_for_display

_PENDING_IMPORT_KEY = "admin_question_import_pending"
_PENDING_IMPORT_META_KEY = "admin_question_import_meta"
_BACKUP_PREPARED_KEY = "admin_backup_prepared"
_UPLOAD_SUCCESS_KEY = "admin_bulk_upload_success"
_UPLOAD_SOURCE_KEY = "admin_bulk_upload_source"
_UPLOAD_FILE_BASE_KEY = "admin_bulk_upload_file"
_UPLOAD_FILE_RESET_KEY = "admin_bulk_upload_file_reset"
_UPLOAD_CLEAR_PENDING_KEY = "admin_bulk_upload_clear_pending"
_DELETE_SUCCESS_KEY = "admin_bulk_delete_success"

_USER_TABLE_COLUMNS = (
    "first_name",
    "last_name",
    "email",
    "role",
    "is_disabled",
    "last_login",
    "created_at",
)


@st.cache_data(ttl=60, show_spinner=False)
def _cached_admin_users() -> list[dict]:
    admin_client = get_supabase_admin_client()
    rows = admin_client.table("users").select("*").execute()
    return rows.data or []


def _sort_users_by_last_login(users: list[dict]) -> list[dict]:
    """Most recent login first; users who never logged in appear last."""
    return sorted(users, key=lambda row: row.get("last_login") or "", reverse=True)


def _rows_for_display(rows: list[dict], datetime_columns: list[str]) -> list[dict]:
    formatted = format_rows_for_display(rows, datetime_columns)
    return [{key: row[key] for key in _USER_TABLE_COLUMNS if key in row} for row in formatted]


def _display_users_table(users: list[dict]) -> None:
    st.dataframe(_rows_for_display(users, ["created_at", "last_login"]), width="stretch")


def _clear_pending_question_import() -> None:
    st.session_state.pop(_PENDING_IMPORT_KEY, None)
    st.session_state.pop(_PENDING_IMPORT_META_KEY, None)


def _reset_bulk_upload_form() -> None:
    st.session_state[_UPLOAD_CLEAR_PENDING_KEY] = True


def _apply_bulk_upload_form_reset() -> None:
    if not st.session_state.pop(_UPLOAD_CLEAR_PENDING_KEY, False):
        return
    st.session_state[_UPLOAD_SOURCE_KEY] = ""
    st.session_state[_UPLOAD_FILE_RESET_KEY] = (
        int(st.session_state.get(_UPLOAD_FILE_RESET_KEY, 0)) + 1
    )


def _render_question_import_review(importer: QuestionImportService) -> None:
    pending = st.session_state.get(_PENDING_IMPORT_KEY)
    meta = st.session_state.get(_PENDING_IMPORT_META_KEY) or {}
    if not pending:
        return

    st.divider()
    st.subheader("Review upload")
    source_name = meta.get("source_name") or ""
    batch_preview = meta.get("source", "")
    if source_name:
        try:
            batch_preview = format_batch_name(source_name)
        except ValueError:
            pass
    st.caption(
        f"File: **{meta.get('filename', 'upload')}** · "
        f"Source: **{source_name or '—'}** · "
        f"Batch name: **{batch_preview}** · "
        f"Questions: **{len(pending)}**"
    )
    if meta.get("llm_assisted"):
        st.info(
            "Gemini mapped columns and filled missing values for this upload. "
            "Review the normalized rows below before approving."
        )
        notes = meta.get("notes") or []
        if notes:
            st.caption("LLM notes: " + " · ".join(str(note) for note in notes))
        column_mapping = meta.get("column_mapping") or {}
        mapped = {
            canonical: uploaded
            for canonical, uploaded in column_mapping.items()
            if uploaded
        }
        if mapped:
            st.caption("Column mapping: " + ", ".join(f"{key} ← {value}" for key, value in mapped.items()))
    progress_log = meta.get("progress_log") or []
    if progress_log:
        with st.expander("Processing log", expanded=bool(meta.get("llm_assisted"))):
            for line in progress_log:
                if line.startswith("  "):
                    st.caption(line.strip())
                else:
                    st.markdown(f"- {line}")
    st.dataframe(payload_to_review_dataframe(pending), width="stretch", hide_index=True)

    approve_col, discard_col = st.columns(2)
    with approve_col:
        if st.button("Approve and import to database", type="primary", width="stretch"):
            try:
                if not source_name.strip():
                    st.error("Source name is required to build the batch name before import.")
                    return
                stamped_payload, batch_label = apply_batch_label(pending, source_name)
                count = importer.insert_payload(stamped_payload)
                _clear_pending_question_import()
                clear_backup_cache()
                st.session_state.pop(_BACKUP_PREPARED_KEY, None)
                st.session_state[_UPLOAD_SUCCESS_KEY] = (
                    f"Imported {count} question(s) into the database "
                    f"with batch name **{batch_label}**."
                )
                _reset_bulk_upload_form()
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(str(exc))
    with discard_col:
        if st.button("Discard review", width="stretch"):
            _clear_pending_question_import()
            st.rerun()


def _render_bulk_download_section() -> None:
    st.subheader("Bulk Download / Backup")
    st.caption(
        "Download the current question bank as CSV or Excel. Files use the same columns as the "
        "import template plus `source`, so you can keep a backup or edit and re-upload later."
    )
    sources = list(cached_backup_sources())
    filter_options = ["All questions", *sources]
    selected_filter = st.selectbox(
        "Backup scope",
        filter_options,
        help="Download the full bank or only one batch/source label.",
    )
    source_filter = None if selected_filter == "All questions" else selected_filter
    source_key = "__all__" if source_filter is None else source_filter

    try:
        backup_count = cached_backup_count(source_key)
    except Exception as exc:
        st.warning(f"Could not count questions for backup: {exc}")
        backup_count = 0

    if backup_count == 0:
        st.info("No questions are available to download yet.")
        return

    st.caption(f"**{backup_count}** question(s) available in this backup scope.")
    if st.button("Prepare backup download", type="secondary", width="stretch"):
        try:
            with st.spinner("Building backup files..."):
                csv_bytes, xlsx_bytes = cached_backup_package(source_key)
            st.session_state[_BACKUP_PREPARED_KEY] = {
                "source_key": source_key,
                "csv": csv_bytes,
                "xlsx": xlsx_bytes,
            }
            st.rerun()
        except Exception as exc:
            st.error(f"Could not build backup: {exc}")
            return

    prepared = st.session_state.get(_BACKUP_PREPARED_KEY)
    if not prepared or prepared.get("source_key") != source_key:
        st.caption("Click **Prepare backup download** to generate CSV and Excel files.")
        return

    backup_col_csv, backup_col_xlsx = st.columns(2)
    with backup_col_csv:
        st.download_button(
            "Download CSV backup",
            data=prepared["csv"],
            file_name=backup_filename("csv", source_filter=source_filter),
            mime="text/csv",
            width="stretch",
        )
    with backup_col_xlsx:
        st.download_button(
            "Download Excel backup",
            data=prepared["xlsx"],
            file_name=backup_filename("xlsx", source_filter=source_filter),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )


def _render_bulk_delete_section() -> None:
    st.subheader("Bulk Delete")
    success_message = st.session_state.pop(_DELETE_SUCCESS_KEY, None)
    if success_message:
        st.success(success_message)

    st.caption(
        "Remove questions from the database by batch/source label, or delete the entire bank. "
        "Download a backup first if you may need the data again."
    )
    sources = list(cached_backup_sources())
    filter_options = ["All questions", *sources]
    selected_filter = st.selectbox(
        "Delete scope",
        filter_options,
        key="admin_bulk_delete_scope",
        help="Delete one batch label or every question in the database.",
    )
    source_filter = None if selected_filter == "All questions" else selected_filter
    source_key = "__all__" if source_filter is None else source_filter

    try:
        delete_count = cached_backup_count(source_key)
    except Exception as exc:
        st.warning(f"Could not count questions for delete scope: {exc}")
        delete_count = 0

    if delete_count == 0:
        st.info("No questions match this delete scope.")
        return

    st.warning(f"This will permanently delete **{delete_count}** question(s).")
    if source_filter is None:
        confirm = st.checkbox(
            "I understand this will delete every question in the database.",
            key="admin_bulk_delete_confirm_all",
        )
    else:
        confirm = st.checkbox(
            f"I understand this will delete all questions in batch `{source_filter}`.",
            key="admin_bulk_delete_confirm_batch",
        )

    if st.button("Delete selected questions", type="primary", width="stretch"):
        if not confirm:
            st.error("Check the confirmation box before deleting.")
            return
        try:
            ok, message = delete_questions(source_filter=source_filter)
            if ok:
                st.session_state.pop(_BACKUP_PREPARED_KEY, None)
                st.session_state[_DELETE_SUCCESS_KEY] = message
                st.rerun()
            else:
                st.error(message)
        except Exception as exc:
            st.error(f"Delete failed: {exc}")


def _render_bulk_upload_section() -> None:
    _apply_bulk_upload_form_reset()

    st.subheader("Bulk Upload Questions")
    success_message = st.session_state.pop(_UPLOAD_SUCCESS_KEY, None)
    if success_message:
        st.success(success_message)
    st.caption(
        "Download a template, fill in your questions, upload the file, review the parsed rows, "
        "then approve to save them in the database."
    )
    template_col_csv, template_col_xlsx = st.columns(2)
    with template_col_csv:
        st.download_button(
            "Download CSV template",
            data=build_template_csv_bytes(),
            file_name=CSV_FILENAME,
            mime="text/csv",
            width="stretch",
        )
    with template_col_xlsx:
        st.download_button(
            "Download Excel template",
            data=build_template_xlsx_bytes(),
            file_name=XLSX_FILENAME,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )

    importer = QuestionImportService()
    question_service = QuestionService()
    upload_widget_key = (
        f"{_UPLOAD_FILE_BASE_KEY}_{int(st.session_state.get(_UPLOAD_FILE_RESET_KEY, 0))}"
    )
    uploaded = st.file_uploader(
        "Upload CSV or Excel",
        type=["csv", "xlsx"],
        key=upload_widget_key,
    )
    today_cst = datetime.now(CST).strftime("%m/%d/%Y")
    source_name = st.text_input(
        "Source name (required)",
        value="",
        placeholder="CollegeBoard",
        key=_UPLOAD_SOURCE_KEY,
        help=(
            "Batch name is built from this source plus today's date in CST. "
            'Example: CollegeBoard → "CollegeBoard-01/25/2026".'
        ),
    )
    if source_name.strip():
        try:
            normalized_source = normalize_source_name(source_name)
            batch_preview = format_batch_name(source_name)
            st.caption(
                f"Batch name on import: **{batch_preview}** "
                f"(source **{normalized_source}** + date **{today_cst}**)"
            )
        except ValueError as exc:
            st.warning(str(exc))

    active_batch = question_service.get_latest_import_source()
    if active_batch:
        st.caption(
            f"Practice and mock exams currently draw from the latest approved batch: **{active_batch}**."
        )

    if uploaded and st.button("Review upload", type="primary"):
        if not source_name.strip():
            st.error('Source name is required. Example: "CollegeBoard" → CollegeBoard-01/25/2026.')
            return
        try:
            batch_label = format_batch_name(source_name)
        except ValueError as exc:
            st.error(str(exc))
            return
        progress_log: list[str] = []
        try:
            with st.status("Reviewing upload...", expanded=True) as status:
                progress = StreamlitImportProgress(status)
                try:
                    progress.step(f"Generated batch label `{batch_label}`")
                    payload, parse_meta = importer.parse_upload_bytes(
                        uploaded.getvalue(),
                        filename=uploaded.name,
                        source=batch_label,
                        progress=progress,
                    )
                    progress.step("Upload review ready")
                    progress.detail(
                        "Approve the normalized rows below to save them to the database."
                    )
                    progress_log = progress.log
                    status.update(label="Upload review ready", state="complete")
                except Exception:
                    progress_log = progress.log
                    status.update(label="Upload review failed", state="error")
                    raise

            st.session_state[_PENDING_IMPORT_KEY] = payload
            st.session_state[_PENDING_IMPORT_META_KEY] = {
                "filename": uploaded.name,
                "source_name": normalize_source_name(source_name),
                "source": batch_label,
                "llm_assisted": parse_meta.get("llm_assisted", False),
                "notes": parse_meta.get("notes", []),
                "column_mapping": parse_meta.get("column_mapping", {}),
                "progress_log": progress_log,
            }
            st.rerun()
        except ValueError as exc:
            if progress_log:
                with st.expander("Processing log before failure", expanded=True):
                    for line in progress_log:
                        if line.startswith("  "):
                            st.caption(line.strip())
                        else:
                            st.markdown(f"- {line}")
            st.error(str(exc))
        except RuntimeError as exc:
            if progress_log:
                with st.expander("Processing log before failure", expanded=True):
                    for line in progress_log:
                        if line.startswith("  "):
                            st.caption(line.strip())
                        else:
                            st.markdown(f"- {line}")
            st.error(str(exc))
        except Exception as exc:
            if progress_log:
                with st.expander("Processing log before failure", expanded=True):
                    for line in progress_log:
                        if line.startswith("  "):
                            st.caption(line.strip())
                        else:
                            st.markdown(f"- {line}")
            st.error(f"Could not parse upload: {exc}")

    _render_question_import_review(importer)

    st.caption(
        "Uploads with mismatched headers or missing values are normalized by Gemini before review. "
        "Source name is required. Batch name is Source + today's date (CST), e.g. CollegeBoard-01/25/2026. "
        "Required columns: `exam_type`, `subject`, `topic`, `difficulty`, `question_text`, "
        "`options`, `answer`, `explanation`. Use `||` between choices, or separate "
        "`option_a`–`option_d` columns. Match the downloadable template."
    )
    st.info(
        "For third-party question banks, only import material you are licensed to store and redistribute."
    )


def _display_login_history(history: list[dict]) -> None:
    rows = [
        {
            "Email": row.get("email") or "—",
            "Status": row.get("status") or "—",
            "IP address": row.get("ip_address") or "—",
            "Location": row.get("location") or "—",
            "Time (CST)": format_cst(row.get("created_at")) or "—",
        }
        for row in history
    ]
    st.dataframe(rows, width="stretch")


def _render_edit_user_form(user: dict, *, current_admin_id: str | None) -> None:
    user_id = user.get("user_id")
    name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
    label = f"{name or 'Unnamed'} — {user.get('email', '')} ({user.get('role', '')})"
    if user.get("is_disabled"):
        label += " · Disabled"

    with st.expander(label):
        st.caption(
            f"Created: {format_cst(user.get('created_at')) or '—'} · "
            f"Last login: {format_cst(user.get('last_login')) or 'Never'}"
        )
        with st.form(f"edit_user_{user_id}"):
            col1, col2 = st.columns(2)
            with col1:
                edit_first = st.text_input("First name", value=user.get("first_name", ""))
            with col2:
                edit_last = st.text_input("Last name", value=user.get("last_name", ""))
            edit_email = st.text_input("Email", value=user.get("email", ""))
            roles = ["student", "teacher", "admin"]
            role_index = roles.index(user.get("role", "student"))
            edit_role = st.selectbox("Role", roles, index=role_index)
            edit_disabled = st.checkbox(
                "Disabled",
                value=bool(user.get("is_disabled")),
                help="Disabled users cannot sign in.",
            )

            st.markdown("**Reset password** (optional)")
            new_password = st.text_input(
                "New password",
                type="password",
                key=f"edit_pwd_{user_id}",
                help="Leave blank to keep the current password.",
            )
            confirm_password = st.text_input(
                "Confirm new password",
                type="password",
                key=f"edit_confirm_pwd_{user_id}",
            )
            require_change = st.checkbox(
                "Require password change on next login",
                value=True,
                key=f"edit_require_change_{user_id}",
            )

            if st.form_submit_button("Save changes", type="primary"):
                if edit_disabled and user_id == current_admin_id:
                    st.error("You cannot disable your own account.")
                    return

                password_to_set = None
                if new_password or confirm_password:
                    if new_password != confirm_password:
                        st.error("Passwords do not match.")
                        return
                    password_to_set = new_password

                ok, message = update_user(
                    user_id=user_id,
                    first_name=edit_first,
                    last_name=edit_last,
                    email=edit_email,
                    role=edit_role,
                    is_disabled=edit_disabled,
                    new_password=password_to_set,
                    require_password_change_on_login=require_change,
                )
                if ok:
                    _cached_admin_users.clear()
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)


def render():
    st.title("Security Administration")
    auth = AuthService()
    auth.require_role({"admin"})

    current_user = auth.current_user()
    current_admin_id = current_user.id if current_user else None

    t1, t2, t3, t4 = st.tabs(
        ["User Management", "Security Logs", "Student Performance", "Question Management"]
    )

    with t1:
        st.subheader("Add User")
        st.caption(
            "Creates account in Supabase Auth and syncs to public.users. "
            "The initial password is temporary—the user must set a new password on first login."
        )
        with st.form("add_user"):
            col1, col2 = st.columns(2)
            with col1:
                first_name = st.text_input("First name")
            with col2:
                last_name = st.text_input("Last name")
            email = st.text_input("Email")
            role = st.selectbox("Role", ["student", "teacher", "admin"])
            password = st.text_input(
                "Initial password",
                type="password",
                help="Temporary password. User must replace it on first login.",
            )
            submitted = st.form_submit_button("Add User")
            if submitted:
                ok, message = create_user(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    role=role,
                    password=password,
                )
                if ok:
                    _cached_admin_users.clear()
                    st.success(message)
                else:
                    st.error(message)

        st.divider()
        st.subheader("All Users")
        st.caption(
            "Sorted by most recent login. Timestamps are shown in Central Time (CST/CDT)."
        )
        try:
            users = _sort_users_by_last_login(_cached_admin_users())
            if not users:
                st.info("No users found.")
            else:
                _display_users_table(users)

            st.divider()
            st.subheader("Edit Users")
            st.caption(
                "Update profile details, role, disabled status, or reset a user's password."
            )
            for user in users:
                _render_edit_user_form(user, current_admin_id=current_admin_id)
        except Exception as exc:
            st.warning(f"Could not load users: {exc}")

    with t2:
        st.subheader("Login History")
        st.caption(
            "Shows email, status, IP address, location, and time in Central Time (CST/CDT)."
        )
        if not login_history_schema_ready():
            st.warning(
                "The `location` column is missing in `login_history`. Run "
                "`app/database/migrations/001_login_history_location.sql` once in "
                "Supabase SQL Editor, then log in again."
            )
        history = fetch_login_history(limit=100)
        if history:
            _display_login_history(history)
        else:
            st.info("No login events yet. History is recorded when users log in or out.")

    with t3:
        st.subheader("Student Performance")
        st.caption("Timestamps are shown in Central Time (CST/CDT).")
        try:
            summary = fetch_student_performance_summary()
            if summary:
                st.dataframe(
                    format_rows_for_display(summary, ["last_activity"]),
                    width="stretch",
                )
            else:
                st.info(
                    "No student activity yet. Performance appears here after students "
                    "complete practice questions or mock exams."
                )
        except Exception as exc:
            st.warning(f"Could not load student performance: {exc}")

        st.divider()
        st.subheader("Exam History")
        try:
            history = fetch_exam_history()
            if history:
                st.dataframe(
                    format_rows_for_display(history, ["completed_at"]),
                    width="stretch",
                )
            else:
                st.info("No mock exams completed yet.")
        except Exception as exc:
            st.warning(f"Could not load exam history: {exc}")

    with t4:
        _render_bulk_upload_section()
        st.divider()
        _render_bulk_download_section()
        st.divider()
        _render_bulk_delete_section()
        st.divider()
        st.subheader("Practice Question Bank")
        st.caption(
            f"Downloads OpenSAT (structured community bank), validates format, removes duplicates, "
            f"and reviews public forum sources — only verified accurate items are added "
            f"(forum dumps are rejected by default). Easy/Medium/Hard loaded for {', '.join(EXAM_TYPES)}. "
            "Official College Board PDF exports: use CSV import above. See docs/QUESTION_SOURCES.md."
        )
        replace_all = st.checkbox(
            "Delete ALL existing questions first",
            value=True,
            help="Removes every question, then downloads and inserts the full OpenSAT bank.",
        )
        if st.button("Download latest question bank"):
            progress = st.progress(0, text="Starting...")
            status = st.empty()

            def on_progress(done: int, total: int, msg: str) -> None:
                progress.progress(done / total, text=msg)
                status.caption(f"{done}/{total} — {msg}")

            try:
                if replace_all:
                    ok, message = reload_exam_catalog(progress_callback=on_progress)
                else:
                    ok, message = seed_bulk_questions(progress_callback=on_progress)
            except Exception as exc:
                progress.progress(1.0, text="Failed")
                st.error(
                    f"Question bank download failed: {exc}. "
                    "Partial questions may already be saved — try running the download again."
                )
            else:
                progress.progress(1.0, text="Done")
                if ok:
                    st.success(message)
                else:
                    st.error(message)
