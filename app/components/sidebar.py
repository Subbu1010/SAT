"""Logged-in and guest sidebar layout."""

from __future__ import annotations

import streamlit as st

from app.authentication.auth_service import AuthService
from app.pages import admin, ai_tutor, analytics, dashboard, mock_exam, practice


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


def _user_details(auth: AuthService) -> tuple[str, str, str, str]:
    user = auth.current_user()
    meta = user.user_metadata or {} if user else {}
    full_name = f"{meta.get('first_name', '')} {meta.get('last_name', '')}".strip() or "Student"
    email = user.email if user else ""
    role = auth.get_user_role() or "student"
    initials = "".join(part[0].upper() for part in full_name.split()[:2]) or "S"
    return full_name, email, role, initials


def render_sidebar_footer(auth: AuthService) -> None:
    """Logout directly below navigation; user card at the bottom."""
    st.markdown('<div class="sidebar-logout-section"></div>', unsafe_allow_html=True)
    if st.button("Logout", type="secondary", use_container_width=True, key="main_logout_btn"):
        auth.logout()
        st.rerun()

    full_name, email, role, initials = _user_details(auth)
    st.markdown('<div class="sidebar-footer-spacer"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="sidebar-user-card">
          <div class="sidebar-user-avatar">{initials}</div>
          <div class="sidebar-user-meta">
            <p class="sidebar-user-name">{full_name}</p>
            <p class="sidebar-user-email">{email}</p>
            <p class="sidebar-user-role">{role.title()}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_navigation_pages(auth: AuthService) -> list[st.Page]:
    pages = [
        st.Page(dashboard.render, title="Dashboard", icon="📊", url_path="dashboard", default=True),
        st.Page(practice.render, title="Practice", icon="✏️", url_path="practice"),
        st.Page(mock_exam.render, title="Mock Exam", icon="⏱️", url_path="mock-exam"),
        st.Page(analytics.render, title="Analytics", icon="📈", url_path="analytics"),
        st.Page(ai_tutor.render, title="AI Tutor", icon="🤖", url_path="ai-tutor"),
    ]
    if auth.get_user_role() == "admin":
        pages.append(st.Page(admin.render, title="Admin", icon="🛡️", url_path="admin"))
    return pages


def render_sidebar_nav(pages: list[st.Page]) -> None:
    """Custom sidebar links — reliable when auth-gated navigation starts mid-session."""
    st.markdown('<p class="sidebar-section-label">Navigation</p>', unsafe_allow_html=True)
    for page in pages:
        if page.visibility == "hidden":
            continue
        st.page_link(page, label=page.title, icon=page.icon, width="stretch")


def _render_login_form(auth: AuthService, *, form_key: str = "login_form") -> None:
    with st.form(form_key):
        email = st.text_input("Email", placeholder="you@school.edu")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        remember = st.checkbox("Remember me", help="Stay signed in for 30 days on this device.")
        if st.form_submit_button("Login", type="primary", use_container_width=True):
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


def render_guest_login_page(auth: AuthService) -> None:
    hero_col, login_col = st.columns([1.35, 1], gap="large")
    with hero_col:
        st.markdown(
            """
            <div class="welcome-hero">
              <p class="welcome-kicker">PSAT / SAT Adaptive Learning</p>
              <h1 class="welcome-title">Prepare smarter with practice, mocks, and AI support.</h1>
              <p class="welcome-copy">
                Sign in to access your dashboard, question bank, timed mock exams,
                analytics, and the AI tutor.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with login_col:
        with st.container(border=True):
            st.markdown("### Sign in")
            st.caption("Use your school account to continue.")
            _render_login_form(auth, form_key="main_login_form")


def render_password_reset_sidebar(auth: AuthService) -> None:
    with st.sidebar:
        render_sidebar_brand()
        st.markdown('<p class="sidebar-section-label">Account setup</p>', unsafe_allow_html=True)
        st.info("Set your password to finish signing in.")
        render_sidebar_footer(auth)
