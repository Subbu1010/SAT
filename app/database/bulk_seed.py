from __future__ import annotations

from app.database.exam_catalog import EXAM_TYPES, group_keys
from app.database.official_loaders.loader import (
    delete_all_questions,
    load_official_questions,
)
from app.database.official_loaders.opensat_loader import OPENSAT_SOURCE

# Backward-compatible aliases.
BULK_SOURCE = OPENSAT_SOURCE
QUESTIONS_PER_GROUP = None


def seed_bulk_questions(
    count_per_group: int | None = None,
    progress_callback=None,
) -> tuple[bool, str]:
    """Load all available digital SAT-style questions (no per-subject cap)."""
    _ = count_per_group
    return load_official_questions(replace_existing=False, progress_callback=progress_callback)


def reload_exam_catalog(
    count_per_group: int | None = None,
    progress_callback=None,
) -> tuple[bool, str]:
    """Delete all questions and reload from the OpenSAT community bank."""
    _ = count_per_group
    return load_official_questions(replace_existing=True, progress_callback=progress_callback)


def delete_bulk_questions() -> tuple[bool, str]:
    return delete_all_questions()


def reseed_bulk_questions(
    count_per_group: int | None = None,
    progress_callback=None,
) -> tuple[bool, str]:
    return reload_exam_catalog(count_per_group=count_per_group, progress_callback=progress_callback)


def exam_bank_ready(min_per_exam: int = 300) -> bool:
    from app.database.supabase_client import get_supabase_admin_client, get_supabase_client
    from app.utils.config import get_config

    cfg = get_config()
    client = (
        get_supabase_admin_client()
        if cfg.supabase_secret_key
        else get_supabase_client()
    )
    try:
        for exam_type in EXAM_TYPES:
            rows = (
                client.table("questions")
                .select("question_id", count="exact")
                .eq("exam_type", exam_type)
                .execute()
            )
            if (rows.count or 0) < min_per_exam:
                return False
        return True
    except Exception:
        return False


bulk_bank_ready = exam_bank_ready

__all__ = [
    "BULK_SOURCE",
    "EXAM_TYPES",
    "QUESTIONS_PER_GROUP",
    "bulk_bank_ready",
    "delete_all_questions",
    "delete_bulk_questions",
    "exam_bank_ready",
    "group_keys",
    "load_official_questions",
    "reload_exam_catalog",
    "reseed_bulk_questions",
    "seed_bulk_questions",
]
