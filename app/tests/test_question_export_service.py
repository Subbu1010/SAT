from unittest.mock import MagicMock, patch

import pandas as pd

from app.services.question_export_service import (
    EXPORT_COLUMNS,
    QuestionExportService,
    backup_filename,
    rows_to_export_records,
)


def test_rows_to_export_records_formats_options_and_source():
    rows = rows_to_export_records(
        [
            {
                "exam_type": "SAT",
                "subject": "Math",
                "topic": "Algebra",
                "difficulty": "Easy",
                "question_text": "2+2?",
                "passage": None,
                "options": ["3", "4", "5", "6"],
                "answer": "4",
                "explanation": "Basic math",
                "strategy_tip": "Add carefully",
                "estimated_time": 45,
                "skill_category": "Arithmetic",
                "source": "CollegeBoard-01/25/2026",
            }
        ]
    )

    assert rows[0]["options"] == "3||4||5||6"
    assert rows[0]["source"] == "CollegeBoard-01/25/2026"
    assert list(rows[0].keys()) == EXPORT_COLUMNS


def test_backup_filename_includes_source_when_filtered():
    name = backup_filename("csv", source_filter="CollegeBoard-01/25/2026")
    assert name.endswith(".csv")
    assert "CollegeBoard-01_25_2026" in name


@patch("app.services.question_export_service._export_client")
def test_build_dataframe_returns_import_compatible_columns(mock_client):
    mock_client.return_value.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
        data=[
            {
                "exam_type": "SAT",
                "subject": "Math",
                "topic": "Algebra",
                "difficulty": "Easy",
                "question_text": "2+2?",
                "passage": "",
                "options": ["4", "5"],
                "answer": "4",
                "explanation": "Math",
                "strategy_tip": "",
                "estimated_time": 60,
                "skill_category": "",
                "source": "OpenSAT-03/15/2026",
                "created_at": "2026-03-15T12:00:00Z",
            }
        ]
    )

    df = QuestionExportService().build_dataframe()

    assert list(df.columns) == EXPORT_COLUMNS
    assert len(df) == 1
    assert df.loc[0, "options"] == "4||5"


@patch("app.services.question_export_service._export_client")
def test_build_backup_package_returns_csv_and_xlsx(mock_client):
    mock_client.return_value.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
        data=[
            {
                "exam_type": "SAT",
                "subject": "Math",
                "topic": "Algebra",
                "difficulty": "Easy",
                "question_text": "2+2?",
                "passage": "",
                "options": ["4", "5"],
                "answer": "4",
                "explanation": "Math",
                "strategy_tip": "",
                "estimated_time": 60,
                "skill_category": "",
                "source": "OpenSAT-03/15/2026",
                "created_at": "2026-03-15T12:00:00Z",
            }
        ]
    )

    csv_bytes, xlsx_bytes = QuestionExportService().build_backup_package()

    assert csv_bytes.startswith(b"exam_type,")
    assert len(xlsx_bytes) > 100
