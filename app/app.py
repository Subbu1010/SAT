from functools import lru_cache
from pathlib import Path

import streamlit as st

from app.authentication.auth_service import AuthService
from app.components.sidebar import (
    build_navigation_pages,
    render_guest_home_page,
    render_guest_sidebar,
    render_password_reset_sidebar,
    render_sidebar_brand,
    render_sidebar_footer,
    render_sidebar_nav,
)
from app.database.bootstrap import run_startup_bootstrap
from app.utils.page_session import remember_rendered_url
from app.utils.theme import inject_app_theme
from app.utils.user_session import ensure_user_session_scope
from app.pages import first_login_reset


@lru_cache(maxsize=1)
def _theme_css_text() -> str:
    css_path = Path(__file__).parent / "styles" / "theme.css"
    return css_path.read_text(encoding="utf-8")


def inject_css():
    st.markdown(f"<style>{_theme_css_text()}</style>", unsafe_allow_html=True)


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
    inject_app_theme()

    auth = AuthService()
    if not auth.is_logged_in() and not st.session_state.get("_cookie_restore_attempted"):
        auth.restore_from_cookies()
        st.session_state["_cookie_restore_attempted"] = True

    if auth.is_logged_in():
        user = auth.current_user()
        if user:
            ensure_user_session_scope(user.id)

        if auth.must_reset_password():
            render_password_reset_sidebar(auth)
            first_login_reset.render()
            return

        pages = build_navigation_pages(auth)
        user_role = auth.get_user_role()
        # Hidden built-in nav; we render explicit page links in the sidebar.
        navigation = st.navigation(pages, position="hidden")

        with st.sidebar:
            render_sidebar_brand()
            render_sidebar_nav(pages)
            render_sidebar_footer(auth, role=user_role)

        navigation.run()
        remember_rendered_url()
        return

    render_guest_sidebar(auth)
    render_guest_home_page()


if __name__ == "__main__":
    main()
