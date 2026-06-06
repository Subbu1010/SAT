"""Per-user Streamlit session keys — never share state across accounts."""

from __future__ import annotations

import streamlit as st

_SCOPE_PREFIX = "u:"


def _active_user_id() -> str:
    user = st.session_state.get("auth_user")
    if user is not None and getattr(user, "id", None):
        return str(user.id)
    return str(st.session_state.get("active_user_id") or "anonymous")


def scoped_key(name: str) -> str:
    """Build a session key namespaced to the signed-in user."""
    return f"{_SCOPE_PREFIX}{_active_user_id()}:{name}"


def scoped_get(name: str, default=None):
    return st.session_state.get(scoped_key(name), default)


def scoped_set(name: str, value) -> None:
    st.session_state[scoped_key(name)] = value


def scoped_pop(name: str, default=None):
    return st.session_state.pop(scoped_key(name), default)


def scoped_has(name: str) -> bool:
    return scoped_key(name) in st.session_state


class _ScopedState:
    """Dict-like access to namespaced session values for the active user."""

    def get(self, name: str, default=None):
        return scoped_get(name, default)

    def __getitem__(self, name: str):
        if not scoped_has(name):
            raise KeyError(name)
        return scoped_get(name)

    def __setitem__(self, name: str, value) -> None:
        scoped_set(name, value)

    def pop(self, name: str, default=None):
        return scoped_pop(name, default)

    def __contains__(self, name: str) -> bool:
        return scoped_has(name)


uss = _ScopedState()


def clear_scoped_prefix(name_prefix: str) -> None:
    """Remove scoped keys for the active user that start with name_prefix."""
    prefix = f"{_SCOPE_PREFIX}{_active_user_id()}:{name_prefix}"
    for key in list(st.session_state.keys()):
        if key.startswith(prefix):
            del st.session_state[key]


def clear_scoped_session_for_user(user_id: str | None = None) -> None:
    """Remove all namespaced keys for one user (or every user if user_id is None)."""
    if user_id:
        prefix = f"{_SCOPE_PREFIX}{user_id}:"
        for key in list(st.session_state.keys()):
            if key.startswith(prefix):
                del st.session_state[key]
        return

    for key in list(st.session_state.keys()):
        if key.startswith(_SCOPE_PREFIX):
            del st.session_state[key]
