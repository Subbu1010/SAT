from pathlib import Path

import streamlit as st

from app.authentication.auth_service import AuthService
from app.database.bootstrap import run_startup_bootstrap
from app.pages import admin, ai_tutor, analytics, dashboard, first_login_reset, mock_exam, practice

st.set_page_config(page_title="SAT", page_icon="🎯", layout="wide")

# Hide Share / Edit / GitHub / Deploy chrome on Streamlit Cloud and local dev.
st.set_option("client.toolbarMode", "minimal")


def inject_css():
    css_path = Path(__file__).parent / "styles" / "theme.css"
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def render_login_sidebar(auth: AuthService) -> None:
    st.sidebar.subheader("Login")
    with st.sidebar.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        remember = st.checkbox("Remember Me", help="Stay signed in for 30 days on this device.")
        if st.form_submit_button("Login", type="primary"):
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


def render_logged_in_sidebar(auth: AuthService) -> None:
    user = auth.current_user()
    meta = user.user_metadata or {}
    full_name = f"{meta.get('first_name', '')} {meta.get('last_name', '')}".strip() or "Student"
    st.sidebar.markdown(f"**Signed in as**  \n{full_name}  \n`{user.email}`")
    if st.sidebar.button("Logout", type="primary"):
        auth.logout()
        st.rerun()


def _bootstrap_once() -> None:
    """Run DB seed/bootstrap only once per browser session (not on every click)."""
    if st.session_state.get("_bootstrap_done"):
        return
    try:
        run_startup_bootstrap()
    except Exception:
        pass
    st.session_state["_bootstrap_done"] = True


def main():
    _bootstrap_once()

    inject_css()

    auth = AuthService()
    if not auth.is_logged_in() and not st.session_state.get("_cookie_restore_attempted"):
        auth.restore_from_cookies()
        st.session_state["_cookie_restore_attempted"] = True

    if auth.is_logged_in():
        render_logged_in_sidebar(auth)
        if auth.must_reset_password():
            first_login_reset.render()
            return

        pages = {
            "Dashboard": dashboard.render,
            "Practice": practice.render,
            "Mock Exam": mock_exam.render,
            "Analytics": analytics.render,
            "AI Tutor": ai_tutor.render,
        }
        if auth.get_user_role() == "admin":
            pages["Admin"] = admin.render

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
