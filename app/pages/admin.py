import streamlit as st

from app.authentication.auth_service import AuthService
from app.database.supabase_client import get_supabase_admin_client
from app.services.admin_user_service import create_user, reset_user_password
from app.services.admin_performance_service import (
    fetch_exam_history,
    fetch_student_performance_summary,
)
from app.services.login_history_service import fetch_login_history
from app.database.bulk_seed import reload_exam_catalog, seed_bulk_questions
from app.database.exam_catalog import EXAM_TYPES
from app.services.question_import_service import QuestionImportService


def render():
    st.title("Security Administration")
    auth = AuthService()
    auth.require_role({"admin"})

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
                    st.success(message)
                else:
                    st.error(message)

        st.divider()
        st.subheader("All Users")
        try:
            admin_client = get_supabase_admin_client()
            rows = admin_client.table("users").select("*").order("created_at", desc=True).execute()
            users = rows.data or []
            if not users:
                st.info("No users found.")
            else:
                st.dataframe(users, use_container_width=True)

            st.divider()
            st.subheader("Reset Password")
            st.caption("Set a new password for any user. Admin access only.")
            for user in users:
                name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                label = f"{name or 'Unnamed'} — {user.get('email', '')} ({user.get('role', '')})"
                with st.expander(label):
                    st.caption(
                        f"User ID: `{user.get('user_id')}` · "
                        f"Last login: {user.get('last_login') or 'Never'}"
                    )
                    with st.form(f"reset_password_{user.get('user_id')}"):
                        new_password = st.text_input(
                            "New password",
                            type="password",
                            key=f"new_pwd_{user.get('user_id')}",
                        )
                        confirm_password = st.text_input(
                            "Confirm new password",
                            type="password",
                            key=f"confirm_pwd_{user.get('user_id')}",
                        )
                        require_change = st.checkbox(
                            "Require password change on next login",
                            value=True,
                            key=f"require_change_{user.get('user_id')}",
                        )
                        if st.form_submit_button("Reset password", type="primary"):
                            if new_password != confirm_password:
                                st.error("Passwords do not match.")
                            else:
                                ok, message = reset_user_password(
                                    user_id=user["user_id"],
                                    new_password=new_password,
                                    require_change_on_login=require_change,
                                )
                                if ok:
                                    st.success(message)
                                else:
                                    st.error(message)
        except Exception as exc:
            st.warning(f"Could not load users: {exc}")

    with t2:
        st.subheader("Login History")
        history = fetch_login_history(limit=100)
        if history:
            st.dataframe(history, use_container_width=True)
        else:
            st.info("No login events yet. History is recorded when users log in or out.")

    with t3:
        st.subheader("Student Performance")
        try:
            summary = fetch_student_performance_summary()
            if summary:
                st.dataframe(summary, use_container_width=True)
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
                st.dataframe(history, use_container_width=True)
            else:
                st.info("No mock exams completed yet.")
        except Exception as exc:
            st.warning(f"Could not load exam history: {exc}")

    with t4:
        st.subheader("Bulk Upload Questions")
        importer = QuestionImportService()
        uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])
        source_name = st.text_input("Source label", value="licensed_question_bank")
        if uploaded and st.button("Import Question Bank"):
            data = uploaded.getvalue()
            try:
                if uploaded.name.endswith(".csv"):
                    result = importer.import_csv_bytes(data, source=source_name)
                else:
                    result = importer.import_excel_bytes(data, source=source_name)
                count = len(result.data or [])
                st.success(f"Imported {count} question(s).")
            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Import failed: {exc}")
        st.caption(
            "Required columns: `exam_type`, `subject`, `topic`, `difficulty`, `question_text`, "
            "`options`, `answer`, `explanation`. Use `||` between choices, or separate "
            "`option_a`–`option_d` columns. Match `app/database/seed_questions.csv`."
        )
        st.info(
            "For third-party question banks, only import material you are licensed to store and redistribute."
        )
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

            if replace_all:
                ok, message = reload_exam_catalog(progress_callback=on_progress)
            else:
                ok, message = seed_bulk_questions(progress_callback=on_progress)
            progress.progress(1.0, text="Done")
            if ok:
                st.success(message)
            else:
                st.error(message)
