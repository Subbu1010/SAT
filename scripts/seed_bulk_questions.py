"""Load 100 questions per exam type, subject, and topic into Supabase."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database.bulk_seed import seed_bulk_questions
from app.database.question_bank import QUESTIONS_PER_GROUP, group_keys


def main() -> int:
    total_groups = len(group_keys())
    print(f"Seeding {QUESTIONS_PER_GROUP} questions x {total_groups} groups...")

    def progress(done: int, total: int, msg: str) -> None:
        print(f"[{done}/{total}] {msg}")

    ok, message = seed_bulk_questions(progress_callback=progress)
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
