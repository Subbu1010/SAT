"""Track page navigation so pages can reset state when users return."""

from __future__ import annotations

import streamlit as st

_LAST_RENDERED_URL = "_sat_last_rendered_url"


def remember_rendered_url() -> None:
    """Store the URL of the page that just finished rendering."""
    st.session_state[_LAST_RENDERED_URL] = getattr(st.context, "url", "") or ""


def returned_to_page(page_path: str) -> bool:
    """True when the user opened this page from a different page on the prior run."""
    last_url = st.session_state.get(_LAST_RENDERED_URL)
    current_url = getattr(st.context, "url", "") or ""
    if not last_url or not current_url or last_url == current_url:
        return False
    return _url_matches_page(current_url, page_path)


def _url_matches_page(url: str, page_path: str) -> bool:
    path = url.rstrip("/").split("?")[0]
    segment = page_path.strip("/")
    return path.endswith(f"/{segment}") or path.endswith(segment)
