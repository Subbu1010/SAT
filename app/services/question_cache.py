"""Cached Supabase reads for practice and mock exams."""

from __future__ import annotations

import streamlit as st

from app.database.official_loaders.bluebook_loader import BLUEBOOK_SOURCE
from app.database.official_loaders.opensat_loader import OPENSAT_SOURCE
from app.database.supabase_client import get_supabase_client
from app.services.question_source import display_batch_label, is_dated_batch_source

QUESTION_SELECT_COLUMNS = (
    "question_id,exam_type,subject,topic,difficulty,skill_category,"
    "question_text,passage,options,answer,explanation,strategy_tip,estimated_time,source"
)

PRACTICE_POOL_LIMIT = 300
MOCK_EXAM_POOL_LIMIT = 120
_CACHE_TTL_SECONDS = 300


def clear_question_cache() -> None:
    _cached_student_batch_context.clear()
    _cached_topics_for_subject.clear()
    _cached_count_questions.clear()
    _cached_get_questions.clear()
    try:
        from app.services.question_export_service import clear_backup_cache

        clear_backup_cache()
    except Exception:
        pass


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def _cached_student_batch_context() -> dict[str, str | None]:
    """Resolve the active student batch source and display label."""
    client = get_supabase_client()
    recent = (
        client.table("questions")
        .select("source, created_at")
        .order("created_at", desc=True)
        .limit(300)
        .execute()
    )
    for row in recent.data or []:
        source = row.get("source")
        if is_dated_batch_source(source):
            created_at = row.get("created_at")
            return {
                "raw_source": source,
                "created_at": created_at,
                "display_label": display_batch_label(source, created_at),
            }

    for legacy_source in (OPENSAT_SOURCE, BLUEBOOK_SOURCE):
        legacy = (
            client.table("questions")
            .select("created_at")
            .eq("source", legacy_source)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if legacy.data:
            created_at = legacy.data[0].get("created_at")
            return {
                "raw_source": legacy_source,
                "created_at": created_at,
                "display_label": display_batch_label(legacy_source, created_at),
            }

    fallback_label = display_batch_label(OPENSAT_SOURCE, None)
    return {
        "raw_source": None,
        "created_at": None,
        "display_label": fallback_label,
    }


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def _cached_topics_for_subject(subject: str) -> tuple[str, ...]:
    client = get_supabase_client()
    result = client.table("questions").select("topic").eq("subject", subject).limit(500).execute()
    topics = sorted({row["topic"] for row in (result.data or []) if row.get("topic")})
    return tuple(topics)


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def _cached_count_questions(
    exam_type: str,
    subject: str,
    difficulty: str | None,
    topic: str | None,
    source: str | None,
) -> int:
    client = get_supabase_client()
    query = (
        client.table("questions")
        .select("question_id", count="exact")
        .eq("exam_type", exam_type)
        .eq("subject", subject)
    )
    if difficulty:
        query = query.eq("difficulty", difficulty)
    if topic:
        query = query.eq("topic", topic)
    if source:
        query = query.eq("source", source)
    result = query.execute()
    return result.count or 0


@st.cache_data(ttl=_CACHE_TTL_SECONDS, show_spinner=False)
def _cached_get_questions(
    exam_type: str,
    subject: str,
    difficulty: str | None,
    topic: str | None,
    source: str | None,
    limit: int,
) -> tuple[dict, ...]:
    client = get_supabase_client()
    query = (
        client.table("questions")
        .select(QUESTION_SELECT_COLUMNS)
        .eq("exam_type", exam_type)
        .eq("subject", subject)
    )
    if difficulty:
        query = query.eq("difficulty", difficulty)
    if topic:
        query = query.eq("topic", topic)
    if source:
        query = query.eq("source", source)
    rows = query.limit(limit).execute().data or []
    return tuple(rows)
