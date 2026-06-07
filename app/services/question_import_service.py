from __future__ import annotations

import io
import json
import re
from types import SimpleNamespace

import pandas as pd

from app.database.insert_retry import insert_batches_resilient, is_transient_db_error
from app.database.supabase_client import get_supabase_client
from app.services.import_progress import ImportProgressReporter, NoOpImportProgress
from app.services.question_cache import clear_question_cache
from app.services.question_source import format_batch_name, normalize_source_name

IMPORT_BATCH_SIZE = 25

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


def _normalize_text(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


_TEXT_FIELDS = (
    "exam_type",
    "subject",
    "topic",
    "difficulty",
    "question_text",
    "answer",
    "explanation",
    "passage",
    "strategy_tip",
    "skill_category",
)


def _clean_import_row(row: dict, source: str) -> dict:
    cleaned = {key: row.get(key, "") for key in ALLOWED_COLUMNS if key in row}
    cleaned["options"] = _parse_options(cleaned.get("options"))
    cleaned["source"] = source
    for field in _TEXT_FIELDS:
        if field in cleaned:
            cleaned[field] = _normalize_text(cleaned[field])
    estimated = cleaned.get("estimated_time")
    if estimated in ("", None) or (isinstance(estimated, float) and pd.isna(estimated)):
        cleaned.pop("estimated_time", None)
    else:
        try:
            cleaned["estimated_time"] = int(float(estimated))
        except (TypeError, ValueError):
            cleaned.pop("estimated_time", None)
    return cleaned


def apply_batch_label(payload: list[dict], source_name: str) -> tuple[list[dict], str]:
    """Stamp every row with Source-MM/DD/YYYY using the current CST date."""
    batch_label = format_batch_name(source_name)
    stamped = [{**row, "source": batch_label} for row in payload]
    return stamped, batch_label


def build_import_payload(df: pd.DataFrame, source: str) -> list[dict]:
    df = _normalize_columns(df)
    df = _combine_split_option_columns(df)
    if _missing_columns(df):
        _raise_missing_columns_error(df)

    payload = [
        _clean_import_row(row, source)
        for row in df.fillna("").to_dict(orient="records")
    ]
    if not payload:
        raise ValueError("No question rows found in the uploaded file.")
    return payload


def payload_to_review_dataframe(payload: list[dict]) -> pd.DataFrame:
    """Flatten import payload for on-screen review before database insert."""
    rows: list[dict] = []
    for index, row in enumerate(payload, start=1):
        options = row.get("options") or []
        if isinstance(options, list):
            options_display = " || ".join(str(option) for option in options)
        else:
            options_display = str(options)
        rows.append(
            {
                "#": index,
                "exam_type": _normalize_text(row.get("exam_type")),
                "subject": _normalize_text(row.get("subject")),
                "topic": _normalize_text(row.get("topic")),
                "difficulty": _normalize_text(row.get("difficulty")),
                "question_text": _normalize_text(row.get("question_text")),
                "options": options_display,
                "answer": _normalize_text(row.get("answer")),
                "explanation": _normalize_text(row.get("explanation")),
                "passage": _normalize_text(row.get("passage")),
                "strategy_tip": _normalize_text(row.get("strategy_tip")),
                "estimated_time": _normalize_text(row.get("estimated_time")),
                "skill_category": _normalize_text(row.get("skill_category")),
                "source": _normalize_text(row.get("source")),
            }
        )
    review_df = pd.DataFrame(rows)
    text_columns = [column for column in review_df.columns if column != "#"]
    review_df[text_columns] = review_df[text_columns].astype(str)
    return review_df


def read_raw_csv_bytes(file_bytes: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(file_bytes))
    if df.empty:
        raise ValueError("The CSV file is empty.")
    return df


def read_raw_excel_bytes(file_bytes: bytes) -> pd.DataFrame:
    last_error: ValueError | None = None
    for header_row in range(8):
        df = pd.read_excel(io.BytesIO(file_bytes), header=header_row)
        if df.empty:
            continue
        if len(df.columns) >= 2:
            return df
        last_error = ValueError(f"Header row {header_row} did not produce usable columns.")
    if last_error:
        raise last_error
    raise ValueError("The Excel file is empty.")


def read_upload_dataframe(file_bytes: bytes, *, filename: str) -> pd.DataFrame:
    if filename.lower().endswith(".csv"):
        return read_raw_csv_bytes(file_bytes)
    return read_raw_excel_bytes(file_bytes)


def parse_excel_bytes(file_bytes: bytes) -> pd.DataFrame:
    last_error: ValueError | None = None
    for header_row in range(8):
        df = pd.read_excel(io.BytesIO(file_bytes), header=header_row)
        if df.empty:
            continue
        df = _normalize_columns(df)
        df = _combine_split_option_columns(df)
        if not _missing_columns(df):
            return df
        last_error = ValueError(
            f"Header row {header_row} is missing: {sorted(_missing_columns(df))}"
        )
    if last_error:
        df = pd.read_excel(io.BytesIO(file_bytes))
        _raise_missing_columns_error(_combine_split_option_columns(_normalize_columns(df)))
    raise ValueError("The Excel file is empty.")


class QuestionImportService:
    def __init__(self):
        self.client = get_supabase_client()

    def parse_upload_bytes(
        self,
        file_bytes: bytes,
        *,
        filename: str,
        source: str,
        use_llm: bool = True,
        progress: ImportProgressReporter | None = None,
    ) -> tuple[list[dict], dict]:
        """Validate an upload and return rows ready for review (no database write)."""
        reporter = progress or NoOpImportProgress()
        file_kind = "CSV" if filename.lower().endswith(".csv") else "Excel"

        reporter.step(f"Reading uploaded {file_kind} file")
        df = read_upload_dataframe(file_bytes, filename=filename)
        reporter.detail(
            f"Loaded {len(df)} row(s) and {len(df.columns)} column(s) from `{filename}`."
        )
        reporter.detail(f"Detected columns: {', '.join(str(column) for column in df.columns)}")

        parse_meta: dict = {"llm_assisted": False, "notes": [], "column_mapping": {}}

        reporter.step("Validating against import template")
        try:
            payload = build_import_payload(df, source)
            reporter.detail("Template headers matched — no LLM mapping required.")
            reporter.step("Formatting question rows for review")
            reporter.detail(f"Prepared {len(payload)} question(s) with batch label `{source}`.")
            return payload, parse_meta
        except ValueError as strict_error:
            reporter.detail(f"Template validation failed: {strict_error}")
            if not use_llm:
                raise strict_error
            try:
                from app.services.question_import_llm_service import normalize_upload_with_llm

                reporter.step("Starting Gemini-assisted column and value normalization")
                normalized_df, llm_meta = normalize_upload_with_llm(df, progress=reporter)
                reporter.step("Building review payload from normalized data")
                payload = build_import_payload(normalized_df, source)
                reporter.detail(f"Prepared {len(payload)} question(s) with batch label `{source}`.")
                parse_meta.update(llm_meta)
                return payload, parse_meta
            except RuntimeError as llm_config_error:
                raise RuntimeError(
                    f"{llm_config_error} Column matching requires GEMINI_API_KEY when the "
                    "upload does not match the template."
                ) from llm_config_error
            except Exception as llm_error:
                raise ValueError(
                    f"{strict_error} LLM-assisted mapping also failed: {llm_error}"
                ) from llm_error

    def insert_payload(self, payload: list[dict]) -> int:
        if not payload:
            raise ValueError("No question rows to import.")

        def _insert_batch(batch: list[dict]) -> None:
            self.client.table("questions").insert(batch).execute()

        try:
            insert_batches_resilient(
                rows=payload,
                insert_batch=_insert_batch,
                batch_size=IMPORT_BATCH_SIZE,
                pause_between_batches_sec=0.1,
            )
        except Exception as exc:
            if is_transient_db_error(exc):
                raise RuntimeError(
                    f"Network error while saving questions: {exc}. Try approving the import again."
                ) from exc
            raise
        clear_question_cache()
        return len(payload)

    def import_dataframe(self, df: pd.DataFrame, source: str):
        payload = build_import_payload(df, source)
        self.insert_payload(payload)
        return SimpleNamespace(data=payload)

    def import_csv_bytes(self, file_bytes: bytes, source: str):
        return self.import_dataframe(pd.read_csv(io.BytesIO(file_bytes)), source)

    def import_excel_bytes(self, file_bytes: bytes, source: str):
        return self.import_dataframe(parse_excel_bytes(file_bytes), source)
