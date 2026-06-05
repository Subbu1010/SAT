import streamlit as st

from app.authentication.auth_service import AuthService

MIN_PASSWORD_LENGTH = 8


def render():
    auth = AuthService()
    auth.require_auth()

    user = auth.current_user()
    st.title("Set your password")
    st.info(
        "Your account was created by an administrator. "
        "Please choose a new password before continuing."
    )
    st.caption(f"Signed in as `{user.email}`")

    with st.form("first_login_reset_form"):
        new_password = st.text_input("New password", type="password")
        confirm_password = st.text_input("Confirm new password", type="password")
        submitted = st.form_submit_button("Save password and continue", type="primary")

        if submitted:
            if len(new_password) < MIN_PASSWORD_LENGTH:
                st.error(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                try:
                    auth.complete_password_reset(new_password)
                    st.success("Password updated. Redirecting to your dashboard...")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not update password: {exc}")
