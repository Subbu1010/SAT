"""Load 100 questions per exam type, subject, and topic into Supabase."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database.bulk_seed import reload_exam_catalog
from app.database.exam_catalog import EXAM_TYPES, QUESTIONS_PER_GROUP, group_keys


def main() -> int:
    total_groups = len(group_keys())
    print(
        f"Reloading {QUESTIONS_PER_GROUP} exam-style questions x {total_groups} groups "
        f"for {', '.join(EXAM_TYPES)}..."
    )

    def progress(done: int, total: int, msg: str) -> None:
        print(f"[{done}/{total}] {msg}")

    ok, message = reload_exam_catalog(progress_callback=progress)
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
