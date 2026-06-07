"""Downloadable CSV/Excel templates for the admin question import flow."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

_TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "database" / "seed_questions.csv"
CSV_FILENAME = "sat_question_import_template.csv"
XLSX_FILENAME = "sat_question_import_template.xlsx"


def _template_dataframe() -> pd.DataFrame:
    return pd.read_csv(_TEMPLATE_PATH)


def build_template_csv_bytes() -> bytes:
    return _TEMPLATE_PATH.read_bytes()


def build_template_xlsx_bytes() -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        _template_dataframe().to_excel(writer, index=False, sheet_name="Questions")
    return buffer.getvalue()
