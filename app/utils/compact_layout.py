"""Tighter vertical spacing for exam-style pages (fonts match default Streamlit)."""

from __future__ import annotations

import streamlit as st

_COMPACT_PAGE_CSS = """
<style>
section.main > div.block-container,
section[data-testid="stMain"] > div.block-container {
  padding-top: 0.75rem !important;
  padding-bottom: 1.5rem !important;
}
section.main h1,
section[data-testid="stMain"] h1 {
  margin-bottom: 0.35rem !important;
  padding-top: 0 !important;
}
section[data-testid="stMain"] h2,
section[data-testid="stMain"] h3 {
  margin-top: 0.25rem !important;
  margin-bottom: 0.35rem !important;
}
div[data-testid="column"] .stSelectbox,
div[data-testid="column"] .stCheckbox,
div[data-testid="column"] .stToggle,
div[data-testid="column"] .stButton {
  margin-bottom: 0.15rem;
}
div[data-testid="stAlert"] {
  padding: 0.45rem 0.7rem;
  margin-bottom: 0.35rem;
}
div[data-testid="stProgress"] {
  margin-bottom: 0.35rem;
}
div[data-testid="stChatMessage"] {
  padding-top: 0.35rem !important;
  padding-bottom: 0.35rem !important;
  margin-bottom: 0.25rem !important;
}
div[data-testid="stChatInput"] {
  padding-top: 0.5rem !important;
  padding-bottom: 0.25rem !important;
}
div[data-testid="stStatusWidget"] {
  margin-bottom: 0.35rem !important;
}
</style>
"""


def inject_compact_spacing() -> None:
    st.markdown(_COMPACT_PAGE_CSS, unsafe_allow_html=True)
