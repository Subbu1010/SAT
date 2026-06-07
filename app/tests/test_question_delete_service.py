from unittest.mock import MagicMock, patch

from app.services.question_delete_service import delete_questions


@patch("app.services.question_delete_service.clear_backup_cache")
@patch("app.services.question_delete_service.clear_question_cache")
@patch("app.services.question_delete_service.delete_all_questions")
def test_delete_questions_all(mock_delete_all, _mock_clear_q, _mock_clear_b):
    mock_delete_all.return_value = (True, "Deleted 10 existing questions.")

    ok, message = delete_questions()

    assert ok is True
    assert "Deleted 10" in message
    mock_delete_all.assert_called_once()


@patch("app.services.question_delete_service.clear_backup_cache")
@patch("app.services.question_delete_service.clear_question_cache")
@patch("app.services.question_delete_service._export_client")
def test_delete_questions_by_source(mock_client, _mock_clear_q, _mock_clear_b):
    table = mock_client.return_value.table.return_value
    table.select.return_value.eq.return_value.execute.return_value = MagicMock(count=3)
    table.delete.return_value.eq.return_value.execute.return_value = MagicMock()

    ok, message = delete_questions(source_filter="CollegeBoard-01/25/2026")

    assert ok is True
    assert "Deleted 3 question(s)" in message
    table.delete.return_value.eq.assert_called_with("source", "CollegeBoard-01/25/2026")
