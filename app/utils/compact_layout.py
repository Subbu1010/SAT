"""Tighter vertical spacing for exam-style pages (fonts match default Streamlit)."""

from __future__ import annotations

import streamlit as st

_COMPACT_PAGE_CSS = """
<style>
section.main > div.block-container {
  padding-top: 0.75rem !important;
  padding-bottom: 1.5rem !important;
}
section.main h1 {
  margin-bottom: 0.35rem !important;
  padding-top: 0 !important;
}
div[data-testid="column"] .stSelectbox,
div[data-testid="column"] .stCheckbox,
div[data-testid="column"] .stToggle {
  margin-bottom: 0.15rem;
}
div[data-testid="stAlert"] {
  padding: 0.45rem 0.7rem;
  margin-bottom: 0.35rem;
}
div[data-testid="stProgress"] {
  margin-bottom: 0.35rem;
}
</style>
"""


def inject_compact_spacing() -> None:
    st.markdown(_COMPACT_PAGE_CSS, unsafe_allow_html=True)
