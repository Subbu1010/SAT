import io

import pandas as pd

from app.services.question_import_service import REQUIRED_COLUMNS
from app.services.question_template import build_template_csv_bytes, build_template_xlsx_bytes


def test_template_csv_has_required_columns():
    df = pd.read_csv(io.BytesIO(build_template_csv_bytes()))
    assert REQUIRED_COLUMNS.issubset(set(df.columns))
    assert len(df) >= 1


def test_template_xlsx_has_required_columns():
    df = pd.read_excel(io.BytesIO(build_template_xlsx_bytes()))
    assert REQUIRED_COLUMNS.issubset(set(df.columns))
    assert len(df) >= 1
