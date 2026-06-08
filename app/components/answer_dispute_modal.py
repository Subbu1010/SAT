"""Dispute popup for practice feedback using a native Streamlit dialog."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from app.services.answer_dispute_service import has_pending_dispute, submit_dispute
from app.utils.page_session import _url_matches_page
from app.utils.scoped_session import scoped_get, scoped_key, scoped_pop, scoped_set

DISPUTE_OPEN_KEY = "practice_dispute_open"
DISPUTE_ERROR_KEY = "practice_dispute_error"
DISPUTE_MESSAGE_KEY = "practice_dispute_message"


def build_dispute_option_choices(display_options: list[str], question: dict) -> list[str]:
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


def submit_dispute_from_form(
    *,
    user_id: str,
    question: dict,
    feedback: dict,
    proposed_answer: str,
    custom_answer: str,
    reason: str,
) -> None:
    question_id = question["question_id"]
    final_answer = custom_answer.strip() or proposed_answer.strip()
    if not final_answer:
        scoped_set(
            DISPUTE_ERROR_KEY,
            "Please choose or enter the answer you believe is correct.",
        )
        scoped_set(DISPUTE_OPEN_KEY, question_id)
        return

    try:
        submit_dispute(
            user_id=user_id,
            question_id=question_id,
            selected_answer=feedback.get("selected", ""),
            stored_answer=str(question.get("answer", "")),
            proposed_answer=final_answer,
            reason=reason,
        )
        scoped_pop(DISPUTE_OPEN_KEY, None)
        scoped_pop(DISPUTE_ERROR_KEY, None)
        scoped_set(DISPUTE_MESSAGE_KEY, "Dispute submitted. An admin will review it soon.")
    except ValueError as exc:
        scoped_set(DISPUTE_ERROR_KEY, str(exc))
        scoped_set(DISPUTE_OPEN_KEY, question_id)
    except Exception as exc:
        scoped_set(DISPUTE_ERROR_KEY, f"Could not submit dispute: {exc}")
        scoped_set(DISPUTE_OPEN_KEY, question_id)


def _on_dispute_dialog_dismiss() -> None:
    scoped_pop(DISPUTE_OPEN_KEY, None)
    scoped_pop(DISPUTE_ERROR_KEY, None)


def _inject_dispute_dialog_position_css() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stModal"] {
          align-items: flex-end !important;
          justify-content: flex-end !important;
        }
        div[data-testid="stModal"] > div {
          margin: 0 18px 18px 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.dialog(
    "Dispute this answer",
    width="small",
    on_dismiss=_on_dispute_dialog_dismiss,
)
def _dispute_dialog(
    question: dict,
    *,
    user_id: str,
    feedback: dict,
    display_options: list[str],
) -> None:
    question_id = question["question_id"]
    st.caption("Select the answer you believe is correct. Comments are optional.")

    error_message = str(scoped_get(DISPUTE_ERROR_KEY, "") or "")
    if error_message:
        st.warning(error_message)

    choices = build_dispute_option_choices(display_options, question)
    with st.form(scoped_key(f"dispute_dialog_form_{question_id}")):
        proposed = st.selectbox(
            "Correct answer (required)",
            options=[""] + choices,
            format_func=lambda value: (
                "Choose the answer you believe is correct" if value == "" else value
            ),
        )
        custom = st.text_input(
            "Or type the correct answer",
            placeholder="Use if your answer is not listed above",
        )
        reason = st.text_area(
            "Comments (optional)",
            placeholder="Add any notes for the admin reviewer.",
            height=100,
        )
        action_col, submit_col = st.columns(2)
        with action_col:
            cancelled = st.form_submit_button("Cancel", type="secondary")
        with submit_col:
            submitted = st.form_submit_button("Submit dispute", type="primary")

    if cancelled:
        _on_dispute_dialog_dismiss()
        st.rerun()

    if submitted:
        submit_dispute_from_form(
            user_id=user_id,
            question=question,
            feedback=feedback,
            proposed_answer=proposed,
            custom_answer=custom,
            reason=reason,
        )
        st.rerun()


def open_dispute_dialog_if_needed(
    question: dict,
    *,
    user_id: str,
    feedback: dict,
    display_options: list[str],
) -> None:
    """Open the dispute dialog when the student clicked Dispute this answer."""
    if scoped_get(DISPUTE_OPEN_KEY) != question["question_id"]:
        return
    _inject_dispute_dialog_position_css()
    _dispute_dialog(
        question,
        user_id=user_id,
        feedback=feedback,
        display_options=display_options,
    )


def _build_dispute_cleanup_script() -> str:
    return """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8" /></head>
<body style="margin:0;padding:0;overflow:hidden;">
<script>
(function () {
  const doc = window.parent && window.parent.document
    ? window.parent.document
    : document;
  doc.getElementById("sat-dispute-modal-practice")?.remove();
  if (!doc.querySelector(".sat-dispute-modal-host")) {
    doc.getElementById("sat-dispute-styles")?.remove();
  }
})();
</script>
</body>
</html>
"""


def inject_dispute_modal_cleanup() -> None:
    """Remove any legacy HTML dispute popup nodes."""
    components.html(_build_dispute_cleanup_script(), height=0, scrolling=False)


def cleanup_dispute_modal_on_disallowed_pages() -> None:
    """Remove legacy dispute popup DOM when the user leaves the Practice page."""
    url = getattr(st.context, "url", "") or ""
    if _url_matches_page(url, "practice"):
        return
    inject_dispute_modal_cleanup()


def show_dispute_feedback_messages(*, user_id: str, question_id: str) -> bool:
    """Show dispute status messages. Returns True when the dispute button may be shown."""
    success_message = scoped_pop(DISPUTE_MESSAGE_KEY, None)
    if success_message:
        st.success(success_message)

    if has_pending_dispute(user_id=user_id, question_id=question_id):
        st.info("Your dispute for this question is pending admin review.")
        inject_dispute_modal_cleanup()
        scoped_pop(DISPUTE_OPEN_KEY, None)
        return False
    return True


def render_dispute_open_button(question_id: str) -> None:
    if st.button(
        "Dispute this answer",
        type="secondary",
        key=scoped_key("practice_dispute_btn"),
    ):
        scoped_set(DISPUTE_OPEN_KEY, question_id)
        scoped_pop(DISPUTE_ERROR_KEY, None)
        st.rerun()
