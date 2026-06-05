import streamlit as st

from app.authentication.auth_service import AuthService
from app.database.supabase_client import get_supabase_admin_client, get_supabase_client
from app.services.admin_user_service import create_user
from app.services.login_history_service import fetch_login_history
from app.database.bulk_seed import seed_bulk_questions
from app.services.question_import_service import QuestionImportService


def render():
    st.title("Security Administration")
    auth = AuthService()
    auth.require_role({"admin"})
    client = get_supabase_client()

    t1, t2, t3, t4 = st.tabs(
        ["User Management", "Security Logs", "Student Performance", "Question Management"]
    )

    with t1:
        st.subheader("Add User")
        st.caption("Creates account in Supabase Auth and syncs to public.users.")
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
                help="User can change this after first login.",
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
            st.dataframe(rows.data or [], use_container_width=True)
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
        st.subheader("Exam and Performance History")
        perf = client.table("performance_analytics").select("*").limit(100).execute()
        st.dataframe(perf.data or [])

    with t4:
        st.subheader("Bulk Upload Questions")
        importer = QuestionImportService()
        uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])
        source_name = st.text_input("Source label", value="licensed_question_bank")
        if uploaded and st.button("Import Question Bank"):
            data = uploaded.getvalue()
            if uploaded.name.endswith(".csv"):
                importer.import_csv_bytes(data, source=source_name)
            else:
                importer.import_excel_bytes(data, source=source_name)
            st.success("Questions imported.")
        st.info(
            "For third-party question banks, only import material you are licensed to store and redistribute."
        )
        st.divider()
        st.subheader("Practice Question Bank")
        st.caption("Loads 100 questions per exam type, subject, and topic (3,000 total). Safe to run again.")
        if st.button("Seed practice bank (100 per topic)"):
            progress = st.progress(0, text="Starting...")
            status = st.empty()

            def on_progress(done: int, total: int, msg: str) -> None:
                progress.progress(done / total, text=msg)
                status.caption(f"{done}/{total} — {msg}")

            ok, message = seed_bulk_questions(progress_callback=on_progress)
            progress.progress(1.0, text="Done")
            if ok:
                st.success(message)
            else:
                st.error(message)
