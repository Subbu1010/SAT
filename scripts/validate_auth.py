"""Validate Supabase seed + login for all test accounts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.authentication.auth_core import sign_in
from app.database.seed import seed_test_users
from app.database.seed_data import DEFAULT_TEST_PASSWORD, TEST_USERS


def main() -> int:
    print("=== Seeding test users ===")
    ok, msg = seed_test_users()
    print(msg)
    if not ok:
        return 1

    print("\n=== Login validation ===")
    failures = 0
    for user in TEST_USERS:
        email = user["email"]
        result = sign_in(email, DEFAULT_TEST_PASSWORD)
        status = "PASS" if result["ok"] else "FAIL"
        print(f"  [{status}] {email} ({user['role']})")
        if not result["ok"]:
            print(f"         {result.get('error')}")
            failures += 1

    print(f"\nPassword: {DEFAULT_TEST_PASSWORD}")
    if failures:
        print(f"\n{failures} login(s) failed.")
        return 1
    print("\nAll test logins passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
