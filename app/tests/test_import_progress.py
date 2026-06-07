from app.services.import_progress import CollectingImportProgress
from app.services.question_import_service import QuestionImportService
from pathlib import Path
from unittest.mock import MagicMock, patch

_TEMPLATE = Path(__file__).resolve().parents[1] / "database" / "seed_questions.csv"


def test_parse_upload_bytes_records_progress_steps():
    service = QuestionImportService()
    progress = CollectingImportProgress()

    with patch.object(QuestionImportService, "__init__", lambda self: None):
        service.client = MagicMock()
        service.parse_upload_bytes(
            _TEMPLATE.read_bytes(),
            filename="seed_questions.csv",
            source="import:test:batch",
            use_llm=False,
            progress=progress,
        )

    assert any("Reading uploaded CSV file" in step for step in progress.steps)
    assert any("Prepared 3 question(s)" in detail for detail in progress.details)
