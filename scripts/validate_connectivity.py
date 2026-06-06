"""Validate Supabase auth/database and Gemini API connectivity."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _mask(value: str | None, visible: int = 6) -> str:
    if not value:
        return "<missing>"
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}...{value[-visible:]}"


def _key_shape(value: str | None) -> str:
    if not value:
        return "missing"
    if value.startswith("sb_publishable_"):
        return "publishable (new)"
    if value.startswith("sb_secret_"):
        return "secret (new)"
    if value.startswith("eyJ"):
        return "legacy JWT"
    return "unknown format"


def check_config() -> bool:
    from app.utils.config import get_config

    cfg = get_config()
    print("=== Configuration ===")
    print(f"  SUPABASE_URL:          {cfg.supabase_url or '<missing>'}")
    print(f"  Publishable key:       {_mask(cfg.supabase_publishable_key)} [{_key_shape(cfg.supabase_publishable_key)}]")
    print(f"  Secret key:            {_mask(cfg.supabase_secret_key)} [{_key_shape(cfg.supabase_secret_key)}]")
    print(f"  GEMINI_API_KEY:        {_mask(cfg.gemini_api_key)}")
    print(f"  GEMINI_BASE_URL:       {cfg.gemini_base_url}")
    print(f"  GEMINI_MODEL:          {cfg.gemini_model}")
    ok = bool(cfg.supabase_url and cfg.supabase_publishable_key)
    print(f"  Config status:         {'PASS' if ok else 'FAIL'}")
    return ok


def check_supabase_auth() -> bool:
    from app.authentication.auth_core import sign_in
    from app.database.seed_data import DEFAULT_TEST_PASSWORD

    print("\n=== Supabase Auth (publishable key) ===")
    result = sign_in("student@test.local", DEFAULT_TEST_PASSWORD)
    if result["ok"]:
        print("  Login test:            PASS (student@test.local)")
        return True
    print(f"  Login test:            FAIL")
    print(f"  Error:                 {result.get('error')}")
    if result.get("hint"):
        print(f"  Hint:                  {result['hint']}")
    return False


def check_supabase_database() -> bool:
    from app.database.supabase_client import get_supabase_client

    print("\n=== Supabase Database (publishable key) ===")
    client = get_supabase_client()
    try:
        users = client.table("users").select("user_id,email,role").limit(3).execute()
        count = len(users.data or [])
        print(f"  users table query:     PASS ({count} row(s) sampled)")
        if users.data:
            for row in users.data:
                print(f"    - {row.get('email')} ({row.get('role')})")
        return True
    except Exception as exc:
        print(f"  users table query:     FAIL")
        print(f"  Error:                 {exc}")
        return False


def check_supabase_admin() -> bool:
    from app.database.supabase_client import get_supabase_admin_client

    print("\n=== Supabase Admin (secret key) ===")
    try:
        admin = get_supabase_admin_client()
        result = admin.table("users").select("user_id", count="exact").limit(1).execute()
        total = getattr(result, "count", None)
        print(f"  admin users query:     PASS (count={total})")
        return True
    except Exception as exc:
        print(f"  admin users query:     FAIL")
        print(f"  Error:                 {exc}")
        return False


def check_gemini() -> bool:
    from app.services.gemini_service import GeminiService

    print("\n=== Gemini API ===")
    try:
        gemini = GeminiService()
        response = gemini.tutor_reply("Reply with exactly: connectivity ok")
        text = (response or "").strip()
        preview = text[:80].replace("\n", " ")
        print(f"  chat completion:       PASS")
        print(f"  Model:                 {gemini.model}")
        print(f"  Response preview:      {preview}")
        return True
    except Exception as exc:
        print(f"  chat completion:       FAIL")
        print(f"  Error:                 {exc}")
        return False


def main() -> int:
    results = [
        ("config", check_config()),
        ("auth", check_supabase_auth()),
        ("database", check_supabase_database()),
        ("admin", check_supabase_admin()),
        ("gemini", check_gemini()),
    ]
    print("\n=== Summary ===")
    for name, ok in results:
        print(f"  {name:10} {'PASS' if ok else 'FAIL'}")

    failed = [name for name, ok in results if not ok]
    if failed:
        print(f"\nFailed checks: {', '.join(failed)}")
        if "auth" in failed:
            print(
                "\nIf you see 'Unregistered API key' on Streamlit Cloud, update "
                "App settings → Secrets there — Cloud secrets override .env."
            )
        return 1
    print("\nAll connectivity checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
