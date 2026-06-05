from __future__ import annotations

import random
from typing import Any


def shuffled_options(question: dict, *, session_key: str) -> list[str]:
    """Return a stable shuffled option list for this question in the session."""
    import streamlit as st

    if session_key not in st.session_state:
        options = [str(opt) for opt in (question.get("options") or []) if str(opt).strip()]
        random.shuffle(options)
        st.session_state[session_key] = options
    return list(st.session_state[session_key])


def clear_shuffled_options(*keys: str) -> None:
    import streamlit as st

    for key in keys:
        st.session_state.pop(key, None)


def shuffle_questions(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a new list with questions in random order."""
    shuffled = [dict(question) for question in questions]
    random.shuffle(shuffled)
    return shuffled


def shuffle_question_choices(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Shuffle MCQ option order for each question (answers stay as option text)."""
    prepared: list[dict[str, Any]] = []
    for question in questions:
        row = dict(question)
        options = [str(opt) for opt in (row.get("options") or []) if str(opt).strip()]
        random.shuffle(options)
        row["options"] = options
        prepared.append(row)
    return prepared
