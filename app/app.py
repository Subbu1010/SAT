from pathlib import Path

import streamlit as st

from app.authentication.auth_service import AuthService
from app.components.sidebar import (
    build_navigation_pages,
    render_guest_login_page,
    render_guest_sidebar,
    render_password_reset_sidebar,
    render_sidebar_brand,
    render_sidebar_footer,
    render_sidebar_nav,
)
from app.database.bootstrap import run_startup_bootstrap
from app.utils.sidebar_reopen import inject_sidebar_reopen_fab
from app.pages import first_login_reset

st.set_page_config(
    page_title="SAT",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state=280,
)

# Hide Share / Edit / GitHub / Deploy chrome on Streamlit Cloud and local dev.
st.set_option("client.toolbarMode", "viewer")


def inject_css():
    css_path = Path(__file__).parent / "styles" / "theme.css"
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


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
    inject_sidebar_reopen_fab()

    auth = AuthService()
    if not auth.is_logged_in() and not st.session_state.get("_cookie_restore_attempted"):
        auth.restore_from_cookies()
        st.session_state["_cookie_restore_attempted"] = True

    if auth.is_logged_in():
        if auth.must_reset_password():
            render_password_reset_sidebar(auth)
            first_login_reset.render()
            return

        pages = build_navigation_pages(auth)
        # Hidden built-in nav; we render explicit page links in the sidebar.
        navigation = st.navigation(pages, position="hidden")

        with st.sidebar:
            render_sidebar_brand()
            render_sidebar_nav(pages)
            render_sidebar_footer(auth)

        navigation.run()
        return

    render_guest_sidebar(auth)
    render_guest_login_page(auth)


if __name__ == "__main__":
    main()
