"""Delete all questions and load the latest OpenSAT digital SAT-style bank."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database.official_loaders.loader import load_official_questions
from app.database.exam_catalog import EXAM_TYPES


def main() -> int:
    print(f"Reloading latest practice questions for {', '.join(EXAM_TYPES)}...")

    def progress(done: int, total: int, msg: str) -> None:
        print(f"[{done}/{total}] {msg}")

    ok, message = load_official_questions(replace_existing=True, progress_callback=progress)
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
