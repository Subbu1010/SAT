"""Student form to report a likely wrong answer on practice questions."""

from __future__ import annotations

import streamlit as st

from app.services.answer_dispute_service import has_pending_dispute, submit_dispute
from app.utils.scoped_session import scoped_key


def _option_choices(display_options: list[str], question: dict) -> list[str]:
    seen: set[str] = set()
    choices: list[str] = []
    for option in display_options:
        text = str(option).strip()
        if text and text not in seen:
            seen.add(text)
            choices.append(text)
    stored_answer = str(question.get("answer", "")).strip()
    if stored_answer and stored_answer not in seen:
        choices.append(stored_answer)
    return choices


def render_answer_dispute_form(
    question: dict,
    *,
    user_id: str,
    selected_answer: str,
    display_options: list[str],
) -> None:
    question_id = question["question_id"]
    if has_pending_dispute(user_id=user_id, question_id=question_id):
        st.info("Your dispute for this question is pending admin review.")
        return

    stored_answer = str(question.get("answer", ""))
    choices = _option_choices(display_options, question)
    form_key = scoped_key(f"practice_dispute_{question_id}")

    with st.expander("Dispute this answer", expanded=not selected_answer == stored_answer):
        st.caption(
            "If you believe the stored correct answer is wrong, tell us which answer should "
            "be correct and why. An admin will review your report."
        )
        with st.form(form_key):
            if choices:
                proposed = st.selectbox(
                    "Correct answer (your view)",
                    choices,
                    index=None,
                    placeholder="Choose the answer you believe is correct",
                )
            else:
                proposed = None
            custom_answer = st.text_input(
                "Or type the correct answer",
                placeholder="Use this if your answer is not listed above",
            )
            reason = st.text_area(
                "Why is the stored answer wrong?",
                placeholder="Explain your reasoning so an admin can verify the fix.",
                height=100,
            )
            submitted = st.form_submit_button("Submit dispute", type="secondary")
            if submitted:
                final_answer = (custom_answer or proposed or "").strip()
                try:
                    submit_dispute(
                        user_id=user_id,
                        question_id=question_id,
                        selected_answer=selected_answer,
                        stored_answer=stored_answer,
                        proposed_answer=final_answer,
                        reason=reason,
                    )
                    st.success("Dispute submitted. An admin will review it soon.")
                    st.rerun()
                except ValueError as exc:
                    st.warning(str(exc))
                except Exception as exc:
                    st.error(f"Could not submit dispute: {exc}")
