from __future__ import annotations

from app.database.supabase_client import get_supabase_admin_client

_location_column_available: bool | None = None


def _login_history_has_location_column() -> bool:
    """Probe once whether the location column exists (older DBs may not have it)."""
    global _location_column_available
    if _location_column_available is not None:
        return _location_column_available
    try:
        get_supabase_admin_client().table("login_history").select("location").limit(1).execute()
        _location_column_available = True
    except Exception:
        _location_column_available = False
    return _location_column_available


def login_history_schema_ready() -> bool:
    """True when login_history supports the location column."""
    return _login_history_has_location_column()


def log_login_event(
    *,
    email: str,
    status: str,
    user_id: str | None = None,
    ip_address: str | None = None,
    location: str | None = None,
) -> None:
    """Record a login attempt (success or failed). Uses secret key to bypass RLS."""
    row = {
        "user_id": user_id,
        "email": email.strip().lower() if email else None,
        "ip_address": ip_address,
        "status": status,
    }
    include_location = location is not None and _login_history_has_location_column()
    if include_location:
        row["location"] = location

    try:
        get_supabase_admin_client().table("login_history").insert(row).execute()
    except Exception:
        if include_location:
            row.pop("location", None)
            try:
                get_supabase_admin_client().table("login_history").insert(row).execute()
            except Exception:
                pass
        # Never block login flow if audit logging fails.


def fetch_login_history(limit: int = 100) -> list[dict]:
    try:
        client = get_supabase_admin_client()
        rows = (
            client.table("login_history")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return rows.data or []
    except Exception:
        return []
