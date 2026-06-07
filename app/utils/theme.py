"""App-wide light/dark theme preference (browser session)."""

from __future__ import annotations

import streamlit as st

THEME_LIGHT = "light"
THEME_DARK = "dark"
THEME_OPTIONS = (THEME_LIGHT, THEME_DARK)
THEME_LABELS = {THEME_LIGHT: "Light", THEME_DARK: "Dark"}
_SESSION_KEY = "app_theme"
_RADIO_KEY = "sidebar_theme_radio"

_THEME_TARGETS = """
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > section.main,
header[data-testid="stHeader"]
"""

_THEME_VARS: dict[str, str] = {
    THEME_LIGHT: """
  --bg: #f0f5fc;
  --bg-soft: #e8f0fa;
  --sidebar-bg: #ffffff;
  --sidebar-bg-soft: #f6f9fe;
  --surface: #ffffff;
  --surface-glass: rgba(255, 255, 255, 0.75);
  --text: #132a4f;
  --muted: #60738f;
  --placeholder: #9aadc4;
  --primary: #2d7ff9;
  --primary-strong: #1262e0;
  --success: #1b9c6e;
  --danger: #e24d4d;
  --shadow: 0 8px 24px rgba(21, 50, 96, 0.08);
  --radius: 16px;
  --border-subtle: rgba(45, 127, 249, 0.12);
  --border-strong: rgba(45, 127, 249, 0.18);
  --btn-secondary-bg: rgba(255, 255, 255, 0.9);
  --btn-secondary-hover: #ffffff;
  --btn-primary-text: #ffffff;
  --btn-disabled-bg: #e8eef5;
  --btn-disabled-text: #8fa3bf;
  --alert-success-bg: rgba(27, 156, 110, 0.14);
  --alert-success-text: #0d5c41;
  --alert-error-bg: rgba(226, 77, 77, 0.14);
  --alert-error-text: #9b2c2c;
  --alert-warning-bg: rgba(255, 170, 0, 0.16);
  --alert-warning-text: #7a5200;
  --alert-info-bg: rgba(45, 127, 249, 0.12);
  --alert-info-text: #1262e0;
  --expand-btn-bg: #ffffff;
  --logout-btn-bg: #ffffff;
  --logout-btn-hover: rgba(226, 77, 77, 0.06);
  --input-bg: #ffffff;
  --input-border: rgba(45, 127, 249, 0.2);
  --code-bg: rgba(45, 127, 249, 0.06);
""",
    THEME_DARK: """
  --bg: #0c1424;
  --bg-soft: #111d33;
  --sidebar-bg: #101a2c;
  --sidebar-bg-soft: #0d1626;
  --surface: #1a2740;
  --surface-glass: rgba(26, 39, 64, 0.82);
  --text: #e8eef8;
  --muted: #8fa3bf;
  --placeholder: #5c708a;
  --primary: #5ba0ff;
  --primary-strong: #2d7ff9;
  --success: #34c38f;
  --danger: #ff7b7b;
  --shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
  --radius: 16px;
  --border-subtle: rgba(91, 160, 255, 0.16);
  --border-strong: rgba(91, 160, 255, 0.24);
  --btn-secondary-bg: rgba(26, 39, 64, 0.95);
  --btn-secondary-hover: #223252;
  --btn-primary-text: #ffffff;
  --btn-disabled-bg: #121c2e;
  --btn-disabled-text: #6b7f99;
  --alert-success-bg: rgba(52, 195, 143, 0.2);
  --alert-success-text: #9ef0c8;
  --alert-error-bg: rgba(255, 123, 123, 0.2);
  --alert-error-text: #ffc9c9;
  --alert-warning-bg: rgba(255, 193, 7, 0.18);
  --alert-warning-text: #ffe08a;
  --alert-info-bg: rgba(91, 160, 255, 0.18);
  --alert-info-text: #b8d4ff;
  --expand-btn-bg: #1a2740;
  --logout-btn-bg: #1a2740;
  --logout-btn-hover: rgba(255, 123, 123, 0.12);
  --input-bg: #152238;
  --input-border: rgba(91, 160, 255, 0.22);
  --code-bg: rgba(91, 160, 255, 0.1);
""",
}


def get_theme() -> str:
    theme = st.session_state.get(_SESSION_KEY, THEME_LIGHT)
    return theme if theme in THEME_OPTIONS else THEME_LIGHT


def set_theme(theme: str) -> None:
    st.session_state[_SESSION_KEY] = theme if theme in THEME_OPTIONS else THEME_LIGHT


def _label_to_theme(label: str) -> str:
    return THEME_LIGHT if label == THEME_LABELS[THEME_LIGHT] else THEME_DARK


def _sync_theme_from_radio() -> None:
    set_theme(_label_to_theme(st.session_state[_RADIO_KEY]))


def inject_app_theme() -> None:
    """Inject active theme variables (Streamlit blocks <script> in markdown)."""
    theme = get_theme()
    vars_block = _THEME_VARS[theme]
    extra = ""
    if theme == THEME_DARK:
        extra = """
[data-testid="stExpandSidebarButton"] button,
[data-testid="stSidebarCollapseButton"] button {
  background: var(--expand-btn-bg) !important;
  border: 1px solid var(--border-strong) !important;
  color: var(--text) !important;
}
[data-testid="stExpandSidebarButton"] button svg,
[data-testid="stSidebarCollapseButton"] button svg,
[data-testid="stExpandSidebarButton"] button svg path,
[data-testid="stSidebarCollapseButton"] button svg path,
[data-testid="stExpandSidebarButton"] button span,
[data-testid="stSidebarCollapseButton"] button span {
  color: var(--text) !important;
  fill: var(--text) !important;
  stroke: var(--text) !important;
}
.stApp section[data-testid="stSidebar"] {
  box-shadow: 4px 0 18px rgba(0, 0, 0, 0.28) !important;
}
.stApp div[data-testid="stAlert"] {
  background-color: var(--surface) !important;
  color: var(--text) !important;
}
.stApp div[data-testid="stChatInput"] > div {
  background-color: var(--input-bg) !important;
  border-color: var(--input-border) !important;
}
.stApp div[data-testid="stChatInput"] textarea,
.stApp [data-testid="stChatInputTextArea"] {
  color: var(--text) !important;
  -webkit-text-fill-color: var(--text) !important;
}
.stApp div[data-testid="stChatInput"] textarea::placeholder,
.stApp [data-testid="stChatInputTextArea"]::placeholder {
  color: var(--placeholder) !important;
  -webkit-text-fill-color: var(--placeholder) !important;
}
.stApp [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
  background-color: var(--input-bg) !important;
  border: 1px solid var(--input-border) !important;
}
.stApp [data-testid="stFileUploader"] button {
  background: var(--btn-secondary-bg) !important;
  color: var(--text) !important;
  border: 1px solid var(--border-strong) !important;
}
.stApp [data-testid="stFileUploader"] button *,
.stApp [data-testid="stFileUploader"] button [data-testid="stIconMaterial"] {
  color: inherit !important;
  fill: currentColor !important;
}
"""
    st.markdown(
        f"<style>{_THEME_TARGETS} {{{vars_block}}}{extra}</style>",
        unsafe_allow_html=True,
    )


def render_theme_selector() -> None:
    """Sidebar control to switch between light and dark appearance."""
    labels = [THEME_LABELS[value] for value in THEME_OPTIONS]
    if _RADIO_KEY not in st.session_state:
        st.session_state[_RADIO_KEY] = THEME_LABELS[get_theme()]

    st.radio(
        "Theme",
        labels,
        horizontal=True,
        key=_RADIO_KEY,
        label_visibility="collapsed",
        on_change=_sync_theme_from_radio,
    )
