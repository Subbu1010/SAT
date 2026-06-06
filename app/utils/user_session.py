"""Clear per-user Streamlit session data when auth identity changes."""

from __future__ import annotations

import streamlit as st

from app.utils.scoped_session import clear_scoped_session_for_user

_PRESERVED_KEYS = frozenset(
    {
        "_bootstrap_done",
        "_cookie_restore_attempted",
        "is_authenticated",
        "auth_user",
        "session_persistent",
        "auth_access_token",
        "auth_refresh_token",
        "active_user_id",
    }
)

# Legacy unprefixed keys from older builds (removed on logout / user switch).
_LEGACY_USER_KEY_PREFIXES = (
    "practice_",
    "exam_",
    "tutor_",
    "topics_",
    "practice_opts_",
)

_LEGACY_USER_KEYS = frozenset({"adaptive_difficulty"})


def _is_legacy_user_session_key(key: str) -> bool:
    if key in _PRESERVED_KEYS or key.startswith("_"):
        return False
    if key in _LEGACY_USER_KEYS:
        return True
    return key.startswith(_LEGACY_USER_KEY_PREFIXES)


def clear_user_session_state() -> None:
    """Drop all per-user page state for the prior account."""
    previous_user_id = st.session_state.get("active_user_id")
    clear_scoped_session_for_user(previous_user_id)
    clear_scoped_session_for_user(None)

    for key in list(st.session_state.keys()):
        if _is_legacy_user_session_key(key):
            del st.session_state[key]


def ensure_user_session_scope(user_id: str | None) -> None:
    """Reset cached page state when a different account signs in."""
    if not user_id:
        clear_user_session_state()
        st.session_state.pop("active_user_id", None)
        return

    previous = st.session_state.get("active_user_id")
    if previous and previous != user_id:
        clear_scoped_session_for_user(previous)
        for key in list(st.session_state.keys()):
            if _is_legacy_user_session_key(key):
                del st.session_state[key]
    st.session_state["active_user_id"] = user_id
