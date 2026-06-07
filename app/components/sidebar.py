"""Logged-in and guest sidebar layout."""

from __future__ import annotations

import streamlit as st

from app.authentication.auth_service import AuthService
from app.utils.sidebar_reopen import inject_sidebar_reopen_fab
from app.utils.theme import render_theme_selector


def render_sidebar_brand() -> None:
    st.markdown(
        """
        <div class="sidebar-brand">
          <p class="sidebar-brand-icon">🎯</p>
          <p class="sidebar-brand-title">SAT Prep</p>
          <p class="sidebar-brand-subtitle">Adaptive learning platform</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _user_details(auth: AuthService, role: str) -> tuple[str, str, str, str]:
    user = auth.current_user()
    meta = user.user_metadata or {} if user else {}
    full_name = f"{meta.get('first_name', '')} {meta.get('last_name', '')}".strip() or "Student"
    email = user.email if user else ""
    initials = "".join(part[0].upper() for part in full_name.split()[:2]) or "S"
    return full_name, email, role, initials


def render_sidebar_footer(auth: AuthService, *, role: str | None = None) -> None:
    """Logout directly below navigation; user card at the bottom."""
    user_role = role or auth.get_user_role() or "student"
    st.markdown('<p class="sidebar-section-label">Appearance</p>', unsafe_allow_html=True)
    render_theme_selector()
    st.markdown('<div class="sidebar-logout-section"></div>', unsafe_allow_html=True)
    if st.button("Logout", type="secondary", width="stretch", key="main_logout_btn"):
        auth.logout()
        st.rerun()

    full_name, email, role_label, initials = _user_details(auth, user_role)
    st.markdown('<div class="sidebar-footer-spacer"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="sidebar-user-card">
          <div class="sidebar-user-avatar">{initials}</div>
          <div class="sidebar-user-meta">
            <p class="sidebar-user-name">{full_name}</p>
            <p class="sidebar-user-email">{email}</p>
            <p class="sidebar-user-role">{role_label.title()}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    inject_sidebar_reopen_fab()


def _render_dashboard() -> None:
    from app.pages.dashboard import render

    render()


def _render_practice() -> None:
    from app.pages.practice import render

    render()


def _render_mock_exam() -> None:
    from app.pages.mock_exam import render

    render()


def _render_analytics() -> None:
    from app.pages.analytics import render

    render()


def _render_ai_tutor() -> None:
    from app.pages.ai_tutor import render

    render()


def _render_admin() -> None:
    from app.pages.admin import render

    render()


def build_navigation_pages(auth: AuthService) -> list[st.Page]:
    role = auth.get_user_role()
    pages = [
        st.Page(_render_dashboard, title="Dashboard", icon="📊", url_path="dashboard", default=True),
        st.Page(_render_practice, title="Practice", icon="✏️", url_path="practice"),
        st.Page(_render_mock_exam, title="Mock Exam", icon="⏱️", url_path="mock-exam"),
        st.Page(_render_analytics, title="Analytics", icon="📈", url_path="analytics"),
        st.Page(_render_ai_tutor, title="AI Tutor", icon="🤖", url_path="ai-tutor"),
    ]
    if role == "admin":
        pages.append(st.Page(_render_admin, title="Admin", icon="🛡️", url_path="admin"))
    return pages


def render_sidebar_nav(pages: list[st.Page]) -> None:
    """Custom sidebar links — reliable when auth-gated navigation starts mid-session."""
    st.markdown('<p class="sidebar-section-label">Navigation</p>', unsafe_allow_html=True)
    for page in pages:
        if page.visibility == "hidden":
            continue
        st.page_link(page, label=page.title, icon=page.icon, width="stretch")


def _clear_login_fields(form_key: str) -> None:
    for field in ("email", "password"):
        st.session_state[f"{form_key}_{field}"] = ""


def _render_login_form(auth: AuthService, *, form_key: str = "login_form") -> None:
    email_key = f"{form_key}_email"
    password_key = f"{form_key}_password"
    clear_pending_key = f"{form_key}_clear_pending"

    # Form submit writes widget values after this run; clear on the next rerun instead.
    if st.session_state.pop(clear_pending_key, False):
        _clear_login_fields(form_key)

    with st.form(form_key):
        email = st.text_input("Email", placeholder="you@school.edu", key=email_key)
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password",
            key=password_key,
        )
        remember = st.checkbox("Remember me", help="Stay signed in for 30 days on this device.")
        login_col, clear_col = st.columns(2)
        with login_col:
            login_clicked = st.form_submit_button("Login", type="primary", width="stretch")
        with clear_col:
            clear_clicked = st.form_submit_button("Clear", width="stretch")

        if clear_clicked:
            st.session_state[clear_pending_key] = True
            st.rerun()

        if login_clicked:
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


def render_guest_sidebar(auth: AuthService) -> None:
    with st.sidebar:
        render_sidebar_brand()
        st.markdown('<p class="sidebar-section-label">Sign in</p>', unsafe_allow_html=True)
        st.caption("Use your school account to continue.")
        _render_login_form(auth, form_key="main_login_form")
        st.markdown('<p class="sidebar-section-label">Appearance</p>', unsafe_allow_html=True)
        render_theme_selector()
        inject_sidebar_reopen_fab()


def render_guest_home_page() -> None:
    from app.pages.guest_home import render

    render()


def render_guest_login_page(auth: AuthService) -> None:
    """Backward-compatible alias for the guest home view."""
    render_guest_home_page()


def render_password_reset_sidebar(auth: AuthService) -> None:
    with st.sidebar:
        render_sidebar_brand()
        st.markdown('<p class="sidebar-section-label">Account setup</p>', unsafe_allow_html=True)
        st.info("Set your password to finish signing in.")
        render_sidebar_footer(auth)
