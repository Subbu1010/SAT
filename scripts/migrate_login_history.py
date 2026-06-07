"""Add login_history.location column to an existing Supabase project."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.utils.config import get_config

MIGRATION_PATH = ROOT / "app" / "database" / "migrations" / "001_login_history_location.sql"
SQL = MIGRATION_PATH.read_text(encoding="utf-8")


def main() -> int:
    cfg = get_config()
    if not cfg.supabase_db_url:
        print("SUPABASE_DB_URL is not set.")
        print("Run this SQL manually in Supabase Dashboard > SQL Editor:")
        print()
        print(SQL)
        return 1

    try:
        import psycopg2
    except ImportError:
        print("Install psycopg2 to run migrations automatically: pip install psycopg2-binary")
        print()
        print(SQL)
        return 1

    with psycopg2.connect(cfg.supabase_db_url, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
        conn.commit()
    print("Added login_history.location column.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
