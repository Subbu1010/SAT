import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from app.services.question_import_service import (
    QuestionImportService,
    apply_batch_label,
    build_import_payload,
    payload_to_review_dataframe,
    read_upload_dataframe,
)
from app.services.question_source import format_batch_name

_TEMPLATE = Path(__file__).resolve().parents[1] / "database" / "seed_questions.csv"


def test_build_import_payload_parses_seed_template():
    df = pd.read_csv(_TEMPLATE)
    payload = build_import_payload(df, source="test_bank")

    assert len(payload) == 3
    assert payload[0]["exam_type"] == "SAT"
    assert isinstance(payload[0]["options"], list)
    assert payload[0]["source"] == "test_bank"


def test_build_import_payload_omits_blank_estimated_time():
    df = pd.read_csv(_TEMPLATE).head(1).copy()
    df["estimated_time"] = ""

    payload = build_import_payload(df, source="test_bank")

    assert "estimated_time" not in payload[0]


def test_payload_to_review_dataframe_formats_options():
    payload = build_import_payload(pd.read_csv(_TEMPLATE), source="test_bank")
    review = payload_to_review_dataframe(payload)

    assert list(review.columns)[0] == "#"
    assert " || " in review.loc[0, "options"]
    assert review.loc[0, "question_text"]


def test_payload_to_review_dataframe_mixed_answer_types_are_arrow_safe():
    import pyarrow as pa

    payload = [
        {
            "exam_type": "SAT",
            "subject": "Math",
            "topic": "Algebra",
            "difficulty": "Easy",
            "question_text": "Numeric answer",
            "options": ["4", "5", "6"],
            "answer": 6,
            "explanation": "Six",
            "source": "test",
        },
        {
            "exam_type": "SAT",
            "subject": "Reading",
            "topic": "Vocab",
            "difficulty": "Medium",
            "question_text": "Text answer",
            "options": ["ONE", "TWO", "THREE", "FOUR"],
            "answer": "FOUR",
            "explanation": "Fourth option",
            "source": "test",
        },
    ]
    review = payload_to_review_dataframe(payload)

    assert review.loc[0, "answer"] == "6"
    assert review.loc[1, "answer"] == "FOUR"
    pa.Table.from_pandas(review)


def test_parse_upload_bytes_does_not_insert():
    service = QuestionImportService()
    csv_bytes = _TEMPLATE.read_bytes()

    with patch.object(QuestionImportService, "__init__", lambda self: None):
        service.client = MagicMock()
        payload, parse_meta = service.parse_upload_bytes(
            csv_bytes,
            filename="seed_questions.csv",
            source="licensed_question_bank",
            use_llm=False,
        )

    service.client.table.assert_not_called()
    assert len(payload) == 3
    assert parse_meta["llm_assisted"] is False


def test_apply_batch_label_stamps_every_row():
    payload = build_import_payload(pd.read_csv(_TEMPLATE), source="preview-batch")
    from datetime import datetime

    from app.utils.datetime_display import CST

    stamped, batch_label = apply_batch_label(
        payload,
        "College Board",
    )
    assert batch_label.startswith("CollegeBoard-")
    assert all(row["source"] == batch_label for row in stamped)


def test_format_batch_name_for_imports():
    from datetime import datetime

    from app.utils.datetime_display import CST

    label = format_batch_name("My Bank", on_date=datetime(2026, 1, 25, tzinfo=CST))
    assert label == "MyBank-01/25/2026"


def test_read_upload_dataframe_reads_csv():
    df = read_upload_dataframe(_TEMPLATE.read_bytes(), filename="seed_questions.csv")
    assert "exam_type" in df.columns


@patch("app.services.question_import_service.insert_batches_resilient")
def test_insert_payload_writes_batches(mock_insert):
    service = QuestionImportService()
    payload = build_import_payload(pd.read_csv(_TEMPLATE), source="licensed_question_bank")

    count = service.insert_payload(payload)

    assert count == 3
    mock_insert.assert_called_once()
