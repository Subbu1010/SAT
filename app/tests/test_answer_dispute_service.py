from unittest.mock import MagicMock, patch

import pytest

from app.services.answer_dispute_service import (
    _DISPUTE_SELECT,
    _attach_related_records,
    fetch_disputes,
    has_pending_dispute,
    resolve_dispute,
    submit_dispute,
)


@patch("app.services.answer_dispute_service.disputes_schema_ready", return_value=True)
@patch("app.services.answer_dispute_service.get_supabase_client")
def test_submit_dispute_inserts_row(mock_client, _schema_ready):
    client = MagicMock()
    mock_client.return_value = client
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    client.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"dispute_id": "d1", "status": "pending"}]
    )

    row = submit_dispute(
        user_id="user-1",
        question_id="q-1",
        selected_answer="B",
        stored_answer="A",
        proposed_answer="C",
        reason="Option C matches the passage.",
    )

    assert row["dispute_id"] == "d1"
    insert_row = client.table.return_value.insert.call_args.args[0]
    assert insert_row["proposed_answer"] == "C"
    assert insert_row["status"] == "pending"


@patch("app.services.answer_dispute_service.disputes_schema_ready", return_value=True)
@patch("app.services.answer_dispute_service.get_supabase_client")
def test_submit_dispute_allows_empty_reason(mock_client, _schema_ready):
    client = MagicMock()
    mock_client.return_value = client
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )
    client.table.return_value.insert.return_value.execute.return_value = MagicMock(
        data=[{"dispute_id": "d1", "status": "pending"}]
    )

    submit_dispute(
        user_id="user-1",
        question_id="q-1",
        selected_answer="B",
        stored_answer="A",
        proposed_answer="C",
        reason="   ",
    )

    insert_row = client.table.return_value.insert.call_args.args[0]
    assert insert_row["reason"] == "No additional comments provided."


@patch("app.services.answer_dispute_service.disputes_schema_ready", return_value=True)
@patch("app.services.answer_dispute_service.get_supabase_client")
def test_has_pending_dispute_true(mock_client, _schema_ready):
    client = MagicMock()
    mock_client.return_value = client
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"dispute_id": "d1"}]
    )

    assert has_pending_dispute(user_id="user-1", question_id="q-1") is True


def test_dispute_select_uses_explicit_user_relationship():
    assert "users!answer_disputes_user_id_fkey" in _DISPUTE_SELECT


@patch("app.services.answer_dispute_service.get_supabase_admin_client")
def test_attach_related_records_enriches_plain_rows(mock_admin):
    admin = MagicMock()
    mock_admin.return_value = admin
    admin.table.return_value.select.return_value.in_.return_value.execute.side_effect = [
        MagicMock(data=[{"question_id": "q-1", "subject": "Math", "topic": "Algebra"}]),
        MagicMock(data=[{"user_id": "user-1", "first_name": "Sam", "last_name": "Lee", "email": "sam@test.local"}]),
    ]

    enriched = _attach_related_records(
        [
            {
                "dispute_id": "d-1",
                "question_id": "q-1",
                "user_id": "user-1",
                "status": "pending",
            }
        ]
    )

    assert enriched[0]["questions"]["subject"] == "Math"
    assert enriched[0]["users"]["email"] == "sam@test.local"


@patch("app.services.answer_dispute_service._attach_related_records")
@patch("app.services.answer_dispute_service._execute_disputes_query")
@patch("app.services.answer_dispute_service.disputes_schema_ready", return_value=True)
def test_fetch_disputes_falls_back_when_join_fails(_schema_ready, mock_execute, mock_attach):
    mock_execute.side_effect = [
        Exception("ambiguous users relationship"),
        MagicMock(
            data=[
                {
                    "dispute_id": "d-1",
                    "question_id": "q-1",
                    "user_id": "user-1",
                    "status": "pending",
                }
            ]
        ),
    ]
    mock_attach.return_value = [
        {
            "dispute_id": "d-1",
            "questions": {"subject": "Math"},
            "users": {"email": "sam@test.local"},
        }
    ]

    rows = fetch_disputes(status="pending", limit=10)

    assert len(rows) == 1
    assert rows[0]["questions"]["subject"] == "Math"
    assert rows[0]["users"]["email"] == "sam@test.local"
    assert mock_execute.call_count == 2


@patch("app.services.answer_dispute_service.clear_question_cache")
@patch("app.services.answer_dispute_service.disputes_schema_ready", return_value=True)
@patch("app.services.answer_dispute_service.get_supabase_admin_client")
def test_resolve_dispute_accept_updates_question(mock_admin, _schema_ready, mock_clear_cache):
    admin = MagicMock()
    mock_admin.return_value = admin
    admin.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[
            {
                "dispute_id": "d1",
                "question_id": "q-1",
                "status": "pending",
                "proposed_answer": "FOUR",
            }
        ]
    )
    admin.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"dispute_id": "d1", "status": "accepted"}]
    )

    result = resolve_dispute(
        dispute_id="d1",
        status="accepted",
        reviewer_id="admin-1",
        corrected_answer="FOUR",
        corrected_explanation="Fourth option is correct.",
    )

    assert result["status"] == "accepted"
    update_calls = admin.table.return_value.update.call_args_list
    question_update = update_calls[0].args[0]
    assert question_update["answer"] == "FOUR"
    assert question_update["explanation"] == "Fourth option is correct."
    mock_clear_cache.assert_called_once()
