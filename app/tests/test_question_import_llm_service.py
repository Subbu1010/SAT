from unittest.mock import MagicMock

import pandas as pd

from app.services.question_import_llm_service import (
    _apply_column_mapping,
    normalize_upload_with_llm,
)


def test_apply_column_mapping_builds_canonical_rows():
    df = pd.DataFrame(
        [
            {
                "Exam": "SAT",
                "Section": "Math",
                "Prompt": "2+2?",
                "A": "3",
                "B": "4",
                "C": "5",
                "D": "6",
                "Key": "B",
                "Why": "Basic addition",
            }
        ]
    )
    mapping = {
        "exam_type": "Exam",
        "subject": "Section",
        "question_text": "Prompt",
        "answer": "Key",
        "explanation": "Why",
    }

    mapped = _apply_column_mapping(df, mapping)

    assert mapped.loc[0, "exam_type"] == "SAT"
    assert mapped.loc[0, "question_text"] == "2+2?"


def test_normalize_upload_with_llm_uses_mapping_and_repair(monkeypatch):
    raw_df = pd.DataFrame(
        [
            {
                "Exam": "SAT",
                "Section": "Math",
                "Prompt": "2+2?",
                "A": "3",
                "B": "4",
                "C": "5",
                "D": "6",
                "Key": "B",
                "Why": "Basic addition",
            }
        ]
    )
    gemini = MagicMock()
    gemini.tutor_reply.side_effect = [
        """
        {
          "header_row_index": 0,
          "column_mapping": {
            "exam_type": "Exam",
            "subject": "Section",
            "topic": null,
            "difficulty": null,
            "question_text": "Prompt",
            "options": null,
            "answer": "Key",
            "explanation": "Why"
          },
          "option_columns": ["A", "B", "C", "D"],
          "notes": "Mapped shorthand headers."
        }
        """,
        """
        {
          "rows": [
            {
              "row_index": 1,
              "exam_type": "SAT",
              "subject": "Math",
              "topic": "Arithmetic",
              "difficulty": "Easy",
              "question_text": "2+2?",
              "options": "3||4||5||6",
              "answer": "B",
              "explanation": "Basic addition"
            }
          ],
          "notes": "Filled topic and difficulty."
        }
        """,
    ]

    normalized_df, meta = normalize_upload_with_llm(raw_df, gemini=gemini)

    assert meta["llm_assisted"] is True
    assert normalized_df.loc[0, "topic"] == "Arithmetic"
    assert normalized_df.loc[0, "difficulty"] == "Easy"
    assert "||" in str(normalized_df.loc[0, "options"])
