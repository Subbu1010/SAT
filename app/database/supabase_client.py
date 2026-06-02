from functools import lru_cache
from typing import Any

try:
    from supabase import Client, create_client
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "Missing 'supabase' package in the active Python environment. "
        "Start the app with: .\\.venv\\Scripts\\python -m streamlit run streamlit_app.py"
    ) from exc

from app.utils.config import get_config


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Client for normal app usage (publishable key)."""
    cfg = get_config()
    return create_client(cfg.supabase_url, cfg.supabase_publishable_key)


@lru_cache(maxsize=1)
def get_supabase_admin_client() -> Client:
    """Client for admin/seed operations (secret/service role key)."""
    cfg = get_config()
    if not cfg.supabase_secret_key:
        raise RuntimeError(
            "Missing Supabase secret key. Set SUPABASE_SECRET_KEY "
            "(or SUPABASE_SERVICE_ROLE_KEY) in .env."
        )
    return create_client(cfg.supabase_url, cfg.supabase_secret_key)


def query_table(table: str, filters: dict[str, Any] | None = None, limit: int = 100):
    client = get_supabase_client()
    query = client.table(table).select("*")
    for key, value in (filters or {}).items():
        query = query.eq(key, value)
    return query.limit(limit).execute()
