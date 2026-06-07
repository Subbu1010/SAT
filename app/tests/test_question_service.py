from unittest.mock import MagicMock, patch

from app.database.official_loaders.opensat_loader import OPENSAT_SOURCE
from app.services.question_cache import _cached_get_questions, _cached_student_batch_context
from app.services.question_service import QuestionService


@patch("app.services.question_cache.get_supabase_client")
def test_get_active_student_batch_label_formats_legacy_opensat_with_date(mock_client):
    _cached_student_batch_context.clear()
    table = mock_client.return_value.table.return_value
    recent_execute = table.select.return_value.order.return_value.limit.return_value.execute
    recent_execute.return_value = MagicMock(data=[])

    legacy_execute = table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute
    legacy_execute.return_value = MagicMock(
        data=[{"created_at": "2026-03-15T18:00:00+00:00"}]
    )

    service = QuestionService()
    assert service.get_active_student_batch_label() == "OpenSAT-03/15/2026"
    assert service.get_latest_import_source() == OPENSAT_SOURCE


@patch("app.services.question_cache.get_supabase_client")
def test_get_active_student_batch_label_uses_dated_admin_batch(mock_client):
    _cached_student_batch_context.clear()
    mock_client.return_value.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[
            {
                "source": "CollegeBoard-01/25/2026",
                "created_at": "2026-01-25T12:00:00Z",
            }
        ]
    )

    service = QuestionService()
    assert service.get_active_student_batch_label() == "CollegeBoard-01/25/2026"
    assert service.get_latest_import_source() == "CollegeBoard-01/25/2026"


@patch("app.services.question_cache.get_supabase_client")
def test_get_questions_for_students_prefers_latest_batch(mock_client):
    _cached_get_questions.clear()
    _cached_student_batch_context.clear()

    table = mock_client.return_value.table.return_value
    batch_execute = table.select.return_value.order.return_value.limit.return_value.execute
    batch_execute.return_value = MagicMock(
        data=[{"source": "CollegeBoard-01/25/2026", "created_at": "2026-01-25T12:00:00Z"}]
    )

    questions_execute = table.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute
    questions_execute.return_value = MagicMock(
        data=[{"question_id": "1", "source": "CollegeBoard-01/25/2026"}]
    )

    service = QuestionService()
    pool = service.get_questions_for_students(exam_type="SAT", subject="Math")

    assert len(pool) == 1
    assert pool[0]["source"] == "CollegeBoard-01/25/2026"
