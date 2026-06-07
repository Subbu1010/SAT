"""Cross-browser multiple-choice answer UI (single integrated picker)."""

from __future__ import annotations

import streamlit as st


def answer_from_widget(options: list[str], widget_value) -> str | None:
    """Map a radio widget value (index or legacy option text) to the answer string."""
    if widget_value is None:
        return None
    if isinstance(widget_value, int) and 0 <= widget_value < len(options):
        return options[widget_value]
    if isinstance(widget_value, str):
        if widget_value in options:
            return widget_value
    return None


def restore_answer_widget(widget_key: str, options: list[str], saved: str | None) -> None:
    """Seed radio widget state from a persisted answer string."""
    if not saved or saved not in options:
        return
    index = options.index(saved)
    if st.session_state.get(widget_key) != index:
        st.session_state[widget_key] = index


def render_answer_selector(
    options: list[str],
    *,
    widget_key: str,
    label: str = "Choose your answer",
    saved: str | None = None,
) -> str | None:
    """Render one vertical radio list showing each answer option as plain text."""
    if not options:
        return None

    restore_answer_widget(widget_key, options, saved)

    indices = list(range(len(options)))
    st.markdown('<div class="mcq-answer-picker">', unsafe_allow_html=True)
    picked = st.radio(
        label,
        indices,
        format_func=lambda index: options[index],
        key=widget_key,
        index=None,
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)
    return answer_from_widget(options, picked)

