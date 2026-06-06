from __future__ import annotations

import io
import json
import re

import pandas as pd

from app.database.supabase_client import get_supabase_client

REQUIRED_COLUMNS = {
    "exam_type",
    "subject",
    "topic",
    "difficulty",
    "question_text",
    "options",
    "answer",
    "explanation",
}

OPTIONAL_COLUMNS = {
    "passage",
    "strategy_tip",
    "estimated_time",
    "skill_category",
}

ALLOWED_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS | {"source"}


def _slugify(name: str) -> str:
    slug = re.sub(r"[^\w\s]", "", str(name).strip().lower())
    return re.sub(r"\s+", "_", slug)


_COLUMN_ALIASES: dict[str, str] = {}
for canonical, aliases in {
    "exam_type": ("exam_type", "exam type", "exam", "test_type", "test type", "test"),
    "subject": ("subject", "section"),
    "topic": ("topic", "domain", "subtopic", "category"),
    "difficulty": ("difficulty", "level", "difficulty_level", "difficulty level"),
    "question_text": (
        "question_text",
        "question text",
        "question",
        "stem",
        "prompt",
        "question_stem",
        "question stem",
    ),
    "options": ("options", "choices", "answer_choices", "answer choices", "answer_options"),
    "answer": ("answer", "correct_answer", "correct answer", "correct", "key"),
    "explanation": ("explanation", "rationale", "solution", "explanation_text"),
    "passage": ("passage", "paragraph", "reading_passage", "reading passage"),
    "strategy_tip": ("strategy_tip", "strategy tip", "strategy", "tip"),
    "estimated_time": ("estimated_time", "estimated time", "time", "time_seconds"),
    "skill_category": ("skill_category", "skill category", "skill", "skills"),
}.items():
    for alias in aliases:
        _COLUMN_ALIASES[_slugify(alias)] = canonical

_OPTION_GROUPS = (
    ("option_a", "option_b", "option_c", "option_d"),
    ("choice_a", "choice_b", "choice_c", "choice_d"),
    ("answer_a", "answer_b", "answer_c", "answer_d"),
)


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed: dict[str, str] = {}
    for column in df.columns:
        slug = _slugify(column)
        renamed[column] = _COLUMN_ALIASES.get(slug, slug)
    return df.rename(columns=renamed)


def _combine_split_option_columns(df: pd.DataFrame) -> pd.DataFrame:
    if "options" in df.columns:
        return df

    for group in _OPTION_GROUPS:
        if all(col in df.columns for col in group):
            df = df.copy()
            df["options"] = df.apply(
                lambda row: "||".join(str(row[col]).strip() for col in group if str(row[col]).strip()),
                axis=1,
            )
            return df
    return df


def _parse_options(value) -> list[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass
    for separator in ("||", "|", ";", "\n"):
        if separator in text:
            return [part.strip() for part in text.split(separator) if part.strip()]
    return [text]


def _missing_columns(df: pd.DataFrame) -> set[str]:
    return REQUIRED_COLUMNS - set(df.columns)


def _raise_missing_columns_error(df: pd.DataFrame) -> None:
    missing = sorted(_missing_columns(df))
    found = sorted(str(column) for column in df.columns)
    raise ValueError(
        "Missing required columns: "
        f"{missing}. Found columns: {found}. "
        "Required headers: exam_type, subject, topic, difficulty, question_text, "
        "options, answer, explanation. Options may also be split across "
        "option_a/option_b/option_c/option_d columns."
    )


class QuestionImportService:
    def __init__(self):
        self.client = get_supabase_client()

    def _prepare_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        df = _normalize_columns(df)
        df = _combine_split_option_columns(df)
        if _missing_columns(df):
            _raise_missing_columns_error(df)
        return df

    def import_dataframe(self, df: pd.DataFrame, source: str):
        df = self._prepare_dataframe(df)

        rows = df.fillna("").to_dict(orient="records")
        payload: list[dict] = []
        for row in rows:
            cleaned = {key: row.get(key, "") for key in ALLOWED_COLUMNS if key in row}
            cleaned["options"] = _parse_options(cleaned.get("options"))
            cleaned["source"] = source
            if cleaned.get("estimated_time") not in ("", None):
                try:
                    cleaned["estimated_time"] = int(float(cleaned["estimated_time"]))
                except (TypeError, ValueError):
                    cleaned.pop("estimated_time", None)
            payload.append(cleaned)

        if not payload:
            raise ValueError("No question rows found in the uploaded file.")
        return self.client.table("questions").insert(payload).execute()

    def import_csv_bytes(self, file_bytes: bytes, source: str):
        df = pd.read_csv(io.BytesIO(file_bytes))
        return self.import_dataframe(df, source)

    def import_excel_bytes(self, file_bytes: bytes, source: str):
        last_error: ValueError | None = None
        for header_row in range(8):
            df = pd.read_excel(io.BytesIO(file_bytes), header=header_row)
            if df.empty:
                continue
            df = _normalize_columns(df)
            df = _combine_split_option_columns(df)
            if not _missing_columns(df):
                return self.import_dataframe(df, source)
            last_error = ValueError(
                f"Header row {header_row} is missing: {sorted(_missing_columns(df))}"
            )
        if last_error:
            df = pd.read_excel(io.BytesIO(file_bytes))
            _raise_missing_columns_error(_combine_split_option_columns(_normalize_columns(df)))
        raise ValueError("The Excel file is empty.")
