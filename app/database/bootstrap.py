from pathlib import Path

from app.database.seed import run_startup_seed
from app.database.supabase_client import get_supabase_admin_client, get_supabase_client
from app.utils.config import get_config

_SCHEMA_SQL_HINT = (
    "One-time setup: open Supabase Dashboard > SQL Editor, paste app/database/schema.sql, and run it."
)
_POOLER_HINT = (
    "Optional: set SUPABASE_DB_URL only if you want automatic schema.sql execution via Postgres."
)


def _tables_exist() -> bool:
    try:
        get_supabase_client().table("questions").select("question_id").limit(1).execute()
        return True
    except Exception:
        return False


def ensure_schema() -> tuple[bool, str]:
    """
    Optional Postgres bootstrap when SUPABASE_DB_URL is configured.
    With only Supabase API keys, run schema.sql manually in the SQL Editor.
    """
    cfg = get_config()
    if not cfg.supabase_db_url:
        if _tables_exist():
            return True, "Database tables detected (API connection OK)."
        return False, f"Tables not found yet. {_SCHEMA_SQL_HINT}"

    schema_path = Path(__file__).with_name("schema.sql")
    if not schema_path.exists():
        return False, f"Skipping Postgres bootstrap: missing {schema_path}. {_SCHEMA_SQL_HINT}"

    try:
        import psycopg2
    except ImportError:
        return False, f"psycopg2 not installed. {_SCHEMA_SQL_HINT}"

    sql = schema_path.read_text(encoding="utf-8")
    try:
        with psycopg2.connect(cfg.supabase_db_url, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
    except Exception as exc:
        return False, f"Postgres bootstrap skipped: {exc}. {_SCHEMA_SQL_HINT}"

    return True, "Database schema applied via SUPABASE_DB_URL."


def ensure_login_history_location_column() -> tuple[bool, str]:
    """Add login_history.location when SUPABASE_DB_URL is configured."""
    cfg = get_config()
    if not cfg.supabase_db_url:
        return True, ""

    try:
        import psycopg2
    except ImportError:
        return True, ""

    migration_path = Path(__file__).with_name("migrations") / "001_login_history_location.sql"
    if not migration_path.exists():
        return True, ""
    sql = migration_path.read_text(encoding="utf-8")
    try:
        with psycopg2.connect(cfg.supabase_db_url, connect_timeout=10) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
        return True, "login_history.location column ensured."
    except Exception as exc:
        return False, f"Could not add login_history.location column: {exc}"


def run_startup_bootstrap() -> list[tuple[str, str]]:
    """
    One-time startup: optional Postgres schema check + seed users/questions.
    Called once per session from app.py (not on every widget click).
    """
    messages: list[tuple[str, str]] = []
    cfg = get_config()

    if cfg.supabase_db_url:
        schema_ok, schema_msg = ensure_schema()
        messages.append(("success" if schema_ok else "info", schema_msg))
        loc_ok, loc_msg = ensure_login_history_location_column()
        if loc_msg:
            messages.append(("success" if loc_ok else "info", loc_msg))
    elif not _tables_exist():
        messages.append(("info", f"Tables not found yet. {_SCHEMA_SQL_HINT}"))

    messages.extend(run_startup_seed())
    return messages
