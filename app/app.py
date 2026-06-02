from pathlib import Path

import streamlit as st

from app.authentication.auth_service import AuthService
from app.database.bootstrap import run_startup_bootstrap
from app.pages import admin, ai_tutor, analytics, dashboard, mock_exam, practice

st.set_page_config(page_title="PSAT/SAT Adaptive Learning Platform", page_icon="🎯", layout="wide")


def inject_css():
    css_path = Path(__file__).parent / "styles" / "theme.css"
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def render_login_sidebar(auth: AuthService) -> None:
    st.sidebar.subheader("Authentication")
    mode = st.sidebar.radio("Mode", ["Login", "Register", "Forgot Password"])
    if mode == "Login":
        with st.sidebar.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            remember = st.checkbox("Remember Me", help="Stay signed in for 30 days on this device.")
            if st.form_submit_button("Login"):
                try:
                    auth.login(email, password, remember)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Login failed: {exc}")
                    if "Invalid login credentials" in str(exc):
                        st.info(
                            "Test logins: admin@test.local / teacher@test.local / "
                            "student@test.local — password **TestPassword123!**"
                        )
    elif mode == "Register":
        with st.sidebar.form("register_form"):
            first_name = st.text_input("First name")
            last_name = st.text_input("Last name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Register"):
                try:
                    auth.register(email, password, first_name, last_name)
                    st.success("Registration complete. Please verify your email.")
                except Exception as exc:
                    st.error(f"Registration failed: {exc}")
    else:
        email = st.sidebar.text_input("Email to reset password")
        if st.sidebar.button("Send Reset Link"):
            auth.forgot_password(email)
            st.sidebar.success("Reset link sent.")


def render_logged_in_sidebar(auth: AuthService) -> None:
    user = auth.current_user()
    meta = user.user_metadata or {}
    full_name = f"{meta.get('first_name', '')} {meta.get('last_name', '')}".strip() or "Student"
    st.sidebar.markdown(f"**Signed in as**  \n{full_name}  \n`{user.email}`")
    if st.sidebar.button("Logout", type="primary"):
        auth.logout()
        st.rerun()


def main():
    try:
        run_startup_bootstrap()
    except Exception:
        pass

    inject_css()

    auth = AuthService()
    if not auth.is_logged_in():
        auth.restore_from_cookies()

    if auth.is_logged_in():
        render_logged_in_sidebar(auth)
        pages = {
            "Dashboard": dashboard.render,
            "Practice": practice.render,
            "Mock Exam": mock_exam.render,
            "Analytics": analytics.render,
            "AI Tutor": ai_tutor.render,
            "Admin": admin.render,
        }
        selected = st.sidebar.radio("Navigation", list(pages.keys()))
        pages[selected]()
        return

    render_login_sidebar(auth)
    st.title("Welcome to the PSAT/SAT Adaptive Learning Platform")
    st.write(
        "Please log in using the panel on the left. Your session will stay active after refresh "
        "until you click **Logout** or close the browser."
    )


if __name__ == "__main__":
    main()
