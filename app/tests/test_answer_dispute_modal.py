from unittest.mock import patch

from app.components.answer_dispute_modal import (
    build_dispute_option_choices,
    submit_dispute_from_form,
)


def test_build_dispute_option_choices_includes_stored_answer():
    choices = build_dispute_option_choices(
        ["A", "B"],
        {"answer": "C"},
    )
    assert choices == ["A", "B", "C"]


@patch("app.components.answer_dispute_modal.submit_dispute")
@patch("app.components.answer_dispute_modal.scoped_set")
@patch("app.components.answer_dispute_modal.scoped_pop")
def test_submit_dispute_from_form_submits_dispute(
    mock_pop,
    mock_set,
    mock_submit,
):
    mock_submit.return_value = {"dispute_id": "d1"}

    submit_dispute_from_form(
        user_id="user-1",
        question={"question_id": "q-1", "answer": "A"},
        feedback={"selected": "C"},
        proposed_answer="B",
        custom_answer="",
        reason="",
    )

    mock_submit.assert_called_once()
    assert mock_submit.call_args.kwargs["proposed_answer"] == "B"
    mock_set.assert_any_call(
        "practice_dispute_message",
        "Dispute submitted. An admin will review it soon.",
    )


@patch("app.components.answer_dispute_modal.scoped_set")
def test_submit_dispute_from_form_requires_answer(mock_set):
    submit_dispute_from_form(
        user_id="user-1",
        question={"question_id": "q-1", "answer": "A"},
        feedback={"selected": "C"},
        proposed_answer="",
        custom_answer="",
        reason="",
    )

    mock_set.assert_any_call(
        "practice_dispute_error",
        "Please choose or enter the answer you believe is correct.",
    )
