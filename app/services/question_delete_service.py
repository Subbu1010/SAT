"""Admin bulk delete operations for the question bank."""

from __future__ import annotations

from app.database.official_loaders.loader import delete_all_questions
from app.services.question_cache import clear_question_cache
from app.services.question_export_service import _export_client, clear_backup_cache


def delete_questions(*, source_filter: str | None = None) -> tuple[bool, str]:
    """Delete all questions or only one batch/source label."""
    if source_filter is None:
        ok, message = delete_all_questions()
    else:
        ok, message = _delete_questions_by_source(source_filter)

    if ok:
        clear_question_cache()
        clear_backup_cache()
    return ok, message


def _count_questions(client, *, source_filter: str | None = None) -> int:
    query = client.table("questions").select("question_id", count="exact")
    if source_filter:
        query = query.eq("source", source_filter)
    result = query.execute()
    return result.count or 0


def _delete_questions_by_source(source_filter: str) -> tuple[bool, str]:
    client = _export_client()
    try:
        count = _count_questions(client, source_filter=source_filter)
        if count == 0:
            return True, f"No questions found for batch `{source_filter}`."
        client.table("questions").delete().eq("source", source_filter).execute()
        return True, f"Deleted {count} question(s) from batch `{source_filter}`."
    except Exception as exc:
        return False, f"Could not delete questions for `{source_filter}`: {exc}"
