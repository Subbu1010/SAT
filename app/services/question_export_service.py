"""Export question bank rows from Supabase for admin backup downloads."""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import streamlit as st

from app.database.supabase_client import get_supabase_admin_client, get_supabase_client
from app.services.question_import_service import _parse_options
from app.utils.config import get_config
from app.utils.datetime_display import CST

PAGE_SIZE = 1000
MAX_SOURCE_SCAN_PAGES = 3

EXPORT_COLUMNS = [
    "exam_type",
    "subject",
    "topic",
    "difficulty",
    "question_text",
    "passage",
    "options",
    "answer",
    "explanation",
    "strategy_tip",
    "estimated_time",
    "skill_category",
    "source",
]

DB_SELECT_COLUMNS = (
    "exam_type,subject,topic,difficulty,question_text,passage,options,answer,"
    "explanation,strategy_tip,estimated_time,skill_category,source,created_at"
)


def _export_client():
    cfg = get_config()
    if cfg.supabase_secret_key:
        return get_supabase_admin_client()
    return get_supabase_client()


def _source_filter_from_key(source_key: str) -> str | None:
    return None if source_key == "__all__" else source_key


def _format_options_for_export(value) -> str:
    return "||".join(_parse_options(value))


def _normalize_export_value(value) -> str | int | float:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return value


def rows_to_export_records(rows: list[dict]) -> list[dict]:
    export_rows: list[dict] = []
    for row in rows:
        export_rows.append(
            {
                "exam_type": _normalize_export_value(row.get("exam_type")),
                "subject": _normalize_export_value(row.get("subject")),
                "topic": _normalize_export_value(row.get("topic")),
                "difficulty": _normalize_export_value(row.get("difficulty")),
                "question_text": _normalize_export_value(row.get("question_text")),
                "passage": _normalize_export_value(row.get("passage")),
                "options": _format_options_for_export(row.get("options")),
                "answer": _normalize_export_value(row.get("answer")),
                "explanation": _normalize_export_value(row.get("explanation")),
                "strategy_tip": _normalize_export_value(row.get("strategy_tip")),
                "estimated_time": _normalize_export_value(row.get("estimated_time")),
                "skill_category": _normalize_export_value(row.get("skill_category")),
                "source": _normalize_export_value(row.get("source")),
            }
        )
    return export_rows


def backup_filename(extension: str, *, source_filter: str | None = None) -> str:
    stamp = datetime.now(CST).strftime("%Y%m%d")
    if source_filter:
        safe_source = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in source_filter)
        return f"sat_questions_backup_{safe_source}_{stamp}.{extension}"
    return f"sat_questions_backup_{stamp}.{extension}"


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def dataframe_to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Questions")
    return buffer.getvalue()


class QuestionExportService:
    def __init__(self):
        self.client = _export_client()

    def fetch_questions(self, *, source_filter: str | None = None) -> list[dict]:
        rows: list[dict] = []
        offset = 0
        while True:
            query = (
                self.client.table("questions")
                .select(DB_SELECT_COLUMNS)
                .order("created_at")
                .range(offset, offset + PAGE_SIZE - 1)
            )
            if source_filter:
                query = query.eq("source", source_filter)
            page = query.execute()
            batch = page.data or []
            if not batch:
                break
            rows.extend(batch)
            if len(batch) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
        return rows

    def count_questions(self, *, source_filter: str | None = None) -> int:
        query = self.client.table("questions").select("question_id", count="exact")
        if source_filter:
            query = query.eq("source", source_filter)
        result = query.execute()
        return result.count or 0

    def list_sources(self) -> list[str]:
        """Collect batch/source labels, scanning newest questions first."""
        sources: set[str] = set()
        offset = 0
        for _ in range(MAX_SOURCE_SCAN_PAGES):
            page = (
                self.client.table("questions")
                .select("source")
                .order("created_at", desc=True)
                .range(offset, offset + PAGE_SIZE - 1)
                .execute()
            )
            batch = page.data or []
            if not batch:
                break
            sources.update(row["source"] for row in batch if row.get("source"))
            if len(batch) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
        return sorted(sources)

    def build_dataframe(self, *, source_filter: str | None = None) -> pd.DataFrame:
        records = rows_to_export_records(self.fetch_questions(source_filter=source_filter))
        if not records:
            return pd.DataFrame(columns=EXPORT_COLUMNS)
        return pd.DataFrame(records, columns=EXPORT_COLUMNS)

    def build_backup_package(self, *, source_filter: str | None = None) -> tuple[bytes, bytes]:
        df = self.build_dataframe(source_filter=source_filter)
        return dataframe_to_csv_bytes(df), dataframe_to_xlsx_bytes(df)


def clear_backup_cache() -> None:
    cached_backup_sources.clear()
    cached_backup_count.clear()
    cached_backup_package.clear()


@st.cache_data(ttl=300, show_spinner=False)
def cached_backup_sources() -> tuple[str, ...]:
    return tuple(QuestionExportService().list_sources())


@st.cache_data(ttl=120, show_spinner=False)
def cached_backup_count(source_key: str) -> int:
    return QuestionExportService().count_questions(
        source_filter=_source_filter_from_key(source_key)
    )


@st.cache_data(ttl=120, show_spinner=False)
def cached_backup_package(source_key: str) -> tuple[bytes, bytes]:
    return QuestionExportService().build_backup_package(
        source_filter=_source_filter_from_key(source_key)
    )
