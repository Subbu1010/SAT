from __future__ import annotations

from app.database.question_bank import BULK_SOURCE, QUESTIONS_PER_GROUP, group_keys
from app.database.question_bank import generate_group
from app.database.supabase_client import get_supabase_admin_client, get_supabase_client
from app.utils.config import get_config

BATCH_SIZE = 50


def _client():
    cfg = get_config()
    if cfg.supabase_secret_key:
        return get_supabase_admin_client()
    return get_supabase_client()


def _count_for_group(client, exam_type: str, subject: str, topic: str) -> int:
    rows = (
        client.table("questions")
        .select("question_id", count="exact")
        .eq("exam_type", exam_type)
        .eq("subject", subject)
        .eq("topic", topic)
        .eq("source", BULK_SOURCE)
        .execute()
    )
    return rows.count or 0


def seed_bulk_questions(
    count_per_group: int = QUESTIONS_PER_GROUP,
    progress_callback=None,
) -> tuple[bool, str]:
    """
    Insert 100 questions per exam_type + subject + topic (idempotent per group).
    """
    client = _client()
    total_inserted = 0
    groups_done = 0
    groups = group_keys()

    for exam_type, subject, topic in groups:
        existing = _count_for_group(client, exam_type, subject, topic)
        if existing >= count_per_group:
            groups_done += 1
            if progress_callback:
                progress_callback(groups_done, len(groups), f"Skip {exam_type}/{subject}/{topic}")
            continue

        needed = count_per_group - existing
        rows = generate_group(exam_type, subject, topic, needed)
        for start in range(0, len(rows), BATCH_SIZE):
            batch = rows[start : start + BATCH_SIZE]
            client.table("questions").insert(batch).execute()
            total_inserted += len(batch)

        groups_done += 1
        if progress_callback:
            progress_callback(
                groups_done,
                len(groups),
                f"Loaded {exam_type} / {subject} / {topic}",
            )

    return True, f"Bulk bank ready. Inserted {total_inserted} new questions ({count_per_group} per group target)."
