from __future__ import annotations

from app.database.official_loaders.forum_verification import collect_verified_forum_questions
from app.database.official_loaders.opensat_loader import OPENSAT_SOURCE, build_opensat_questions
from app.database.official_loaders.bluebook_loader import BLUEBOOK_SOURCE, build_bluebook_questions
from app.database.official_loaders.validation import dedupe_rows, question_fingerprint
from app.database.supabase_client import get_supabase_admin_client, get_supabase_client
from app.utils.config import get_config

BATCH_SIZE = 50
PAGE_SIZE = 1000


def _client():
    cfg = get_config()
    if cfg.supabase_secret_key:
        return get_supabase_admin_client()
    return get_supabase_client()


def delete_all_questions() -> tuple[bool, str]:
    client = _client()
    try:
        count_before = (
            client.table("questions").select("question_id", count="exact").execute().count or 0
        )
        if count_before == 0:
            return True, "Question bank is already empty."
        client.table("questions").delete().neq(
            "question_id", "00000000-0000-0000-0000-000000000000"
        ).execute()
        return True, f"Deleted {count_before} existing questions."
    except Exception as exc:
        return False, str(exc)


def delete_non_official_questions() -> tuple[bool, str]:
    """Remove legacy/generated banks; keep only the OpenSAT digital SAT-style source."""
    client = _client()
    try:
        client.table("questions").delete().neq("source", OPENSAT_SOURCE).execute()
        return True, "Removed non-OpenSAT question sources."
    except Exception as exc:
        return False, str(exc)


def remove_duplicate_questions() -> tuple[bool, str]:
    """Delete duplicate rows already stored in Supabase, keeping the earliest row."""
    client = _client()
    try:
        offset = 0
        all_rows: list[dict] = []
        while True:
            page = (
                client.table("questions")
                .select("question_id,exam_type,question_text,answer,options,passage,created_at")
                .order("created_at")
                .range(offset, offset + PAGE_SIZE - 1)
                .execute()
            )
            batch = page.data or []
            if not batch:
                break
            all_rows.extend(batch)
            if len(batch) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

        seen: set[str] = set()
        duplicate_ids: list[str] = []
        for row in all_rows:
            key = question_fingerprint(row)
            if key in seen:
                duplicate_ids.append(row["question_id"])
            else:
                seen.add(key)

        if not duplicate_ids:
            return True, "No duplicate questions found."

        for start in range(0, len(duplicate_ids), PAGE_SIZE):
            chunk = duplicate_ids[start : start + PAGE_SIZE]
            client.table("questions").delete().in_("question_id", chunk).execute()

        return True, f"Removed {len(duplicate_ids)} duplicate questions."
    except Exception as exc:
        return False, str(exc)


def load_official_questions(
    *,
    replace_existing: bool = True,
    progress_callback=None,
) -> tuple[bool, str]:
    """
    Load the latest digital SAT-style questions from the OpenSAT JSON database.

    College Board Educator Question Bank has no public API. Export official PDFs and
    import through Admin CSV when you have licensed content.
    """
    if replace_existing:
        ok, message = delete_all_questions()
        if not ok:
            return False, message
    else:
        delete_non_official_questions()
        remove_duplicate_questions()
        message = "Cleaned legacy sources and duplicates."

    rows: list[dict] = []
    stats: dict[str, int] = {}
    try:
        opensat_rows, opensat_stats = build_opensat_questions()
        rows.extend(opensat_rows)
        stats.update({f"opensat_{k}": v for k, v in opensat_stats.items()})
    except Exception as exc:
        return False, f"OpenSAT loader failed: {exc}"

    try:
        bluebook_rows, bluebook_stats = build_bluebook_questions()
        rows.extend(bluebook_rows)
        stats.update(bluebook_stats)
    except Exception:
        # Bluebook loader is best-effort; do not fail the whole reload.
        stats.setdefault("bluebook_loaded", 0)

    if not rows:
        return False, "No valid questions were returned from the OpenSAT source."

    forum_rows, forum_report = collect_verified_forum_questions(existing_rows=rows)
    rows.extend(forum_rows)

    rows, merge_dupes = dedupe_rows(rows)
    stats["merge_duplicates_removed"] = merge_dupes

    client = _client()
    total_batches = (len(rows) + BATCH_SIZE - 1) // BATCH_SIZE
    for batch_index, start in enumerate(range(0, len(rows), BATCH_SIZE)):
        batch = rows[start : start + BATCH_SIZE]
        client.table("questions").insert(batch).execute()
        if progress_callback:
            progress_callback(
                batch_index + 1,
                total_batches,
                f"Inserted {min(start + len(batch), len(rows))}/{len(rows)} questions",
            )

    by_exam: dict[str, int] = {}
    by_subject: dict[str, int] = {}
    by_difficulty: dict[str, int] = {}
    by_source: dict[str, int] = {}
    for row in rows:
        by_exam[row["exam_type"]] = by_exam.get(row["exam_type"], 0) + 1
        by_subject[row["subject"]] = by_subject.get(row["subject"], 0) + 1
        by_difficulty[row["difficulty"]] = by_difficulty.get(row["difficulty"], 0) + 1
        by_source[row.get("source", "unknown")] = by_source.get(row.get("source", "unknown"), 0) + 1

    exam_summary = ", ".join(f"{exam}: {count}" for exam, count in sorted(by_exam.items()))
    subject_summary = ", ".join(f"{subj}: {count}" for subj, count in sorted(by_subject.items()))
    diff_summary = ", ".join(f"{diff}: {count}" for diff, count in sorted(by_difficulty.items()))
    source_summary = ", ".join(f"{src}: {count}" for src, count in sorted(by_source.items()))
    opensat_invalid = stats.get("opensat_source_invalid_removed", 0)
    opensat_dupes = stats.get("opensat_source_duplicates_removed", 0) + stats.get(
        "opensat_row_duplicates_removed", 0
    )
    bluebook_count = stats.get("bluebook_loaded", 0)
    merge_dupes = stats.get("merge_duplicates_removed", 0)
    return (
        True,
        f"Loaded {len(rows)} validated questions (no duplicates). "
        f"Exams — {exam_summary}. Subjects — {subject_summary}. "
        f"Difficulty — {diff_summary}. Sources — {source_summary}. "
        f"Bluebook official: {bluebook_count}. "
        f"Skipped {opensat_invalid} invalid OpenSAT items, "
        f"{opensat_dupes} OpenSAT dupes, {merge_dupes} cross-source dupes. "
        f"{forum_report.summary()}",
    )
