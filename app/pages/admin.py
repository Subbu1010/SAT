import streamlit as st

from app.authentication.auth_service import AuthService
from app.database.supabase_client import get_supabase_client
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
        st.subheader("Add / Enable / Disable / Assign Roles")
        with st.form("add_user"):
            email = st.text_input("Email")
            role = st.selectbox("Role", ["student", "teacher", "admin"])
            submitted = st.form_submit_button("Add User")
            if submitted:
                client.table("users").insert({"email": email, "role": role}).execute()
                st.success("User added.")

    with t2:
        st.subheader("Login History")
        rows = client.table("login_history").select("*").order("created_at", desc=True).limit(50).execute()
        st.dataframe(rows.data or [])

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
