"""CLI wrapper for seeding test users (also runs automatically on app startup)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database.seed import seed_sample_questions, seed_test_users


def main() -> None:
    user_ok, user_msg = seed_test_users()
    print(user_msg)
    if not user_ok:
        sys.exit(1)

    q_ok, q_msg = seed_sample_questions()
    print(q_msg)
    if not q_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
