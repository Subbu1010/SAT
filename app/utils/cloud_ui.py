"""Streamlit Community Cloud viewer chrome helpers."""

from __future__ import annotations

import streamlit as st

from app.authentication.auth_service import AuthService

_CLOUD_HOSTS = ("streamlit.app", "streamlitapp.com")


def is_streamlit_cloud() -> bool:
    try:
        url = (st.context.url or "").lower()
    except Exception:
        return False
    return any(host in url for host in _CLOUD_HOSTS)


def apply_embed_view_for_non_admin(auth: AuthService) -> None:
    """
    Use Streamlit embed mode for students/teachers on Community Cloud.

    This removes in-app toolbar/footer chrome. The Cloud "Manage app" button is
    only shown by Streamlit to GitHub repo owners, not SAT app roles.
    """
    if st.session_state.get("_embed_view_applied"):
        return
    if not is_streamlit_cloud():
        st.session_state["_embed_view_applied"] = True
        return
    if auth.is_logged_in() and auth.get_user_role() == "admin":
        st.session_state["_embed_view_applied"] = True
        return
    if st.query_params.get("embed") == "true":
        st.session_state["_embed_view_applied"] = True
        return

    st.query_params["embed"] = "true"
    st.session_state["_embed_view_applied"] = True
    st.rerun()
