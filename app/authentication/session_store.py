"""Persist Supabase auth session across page refreshes using browser cookies."""

from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache

import extra_streamlit_components as stx
import streamlit as st
from supabase import Client

from app.utils.user_session import ensure_user_session_scope

COOKIE_ACCESS = "sat_access_token"
COOKIE_REFRESH = "sat_refresh_token"


@lru_cache(maxsize=1)
def _cookie_manager() -> stx.CookieManager:
    # Do NOT cache this function with st.cache_*: it creates a widget.
    # Streamlit manages widget identity by the 'key'.
    return stx.CookieManager(key="sat_auth_cookie_manager")


def _cookies_loaded() -> bool:
    """CookieManager returns None until the browser cookie jar is available."""
    return _cookie_manager().get_all(key="get_all_cookies") is not None


def save_session_tokens(session, remember_me: bool) -> None:
    if not session or not getattr(session, "access_token", None):
        return

    cm = _cookie_manager()
    if remember_me:
        expires = datetime.now() + timedelta(days=30)
    else:
        # Survives refresh; cleared when browser session ends (typical session length).
        expires = datetime.now() + timedelta(hours=12)

    cm.set(
        COOKIE_ACCESS,
        session.access_token,
        key="set_access_token",
        expires_at=expires,
    )
    cm.set(
        COOKIE_REFRESH,
        session.refresh_token,
        key="set_refresh_token",
        expires_at=expires,
    )
    st.session_state["session_persistent"] = remember_me


def clear_session_tokens() -> None:
    cm = _cookie_manager()
    try:
        cm.delete(COOKIE_ACCESS, key="delete_access_token")
        cm.delete(COOKIE_REFRESH, key="delete_refresh_token")
    except Exception:
        pass


def restore_session(client: Client) -> bool:
    """Restore Supabase session from cookies into Streamlit session state."""
    if st.session_state.get("is_authenticated") and st.session_state.get("auth_user"):
        return True

    if not _cookies_loaded():
        return False

    access = _cookie_manager().get_all(key="get_tokens") or {}
    refresh = access.get(COOKIE_REFRESH)
    access_token = access.get(COOKIE_ACCESS)
    if not access_token or not refresh:
        return False

    try:
        response = client.auth.set_session(access_token, refresh)
    except Exception:
        clear_session_tokens()
        return False

    if not response or not response.user:
        clear_session_tokens()
        return False

    st.session_state["auth_user"] = response.user
    st.session_state["is_authenticated"] = True
    st.session_state["auth_user_role"] = (response.user.user_metadata or {}).get("role", "student")
    if response.session:
        st.session_state["auth_access_token"] = response.session.access_token
        st.session_state["auth_refresh_token"] = response.session.refresh_token
    ensure_user_session_scope(response.user.id)
    return True


def wait_for_cookies() -> None:
    """Non-blocking cookie warm-up."""
    _cookies_loaded()
