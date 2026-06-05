from __future__ import annotations

from app.database.supabase_client import get_supabase_admin_client


def log_login_event(
    *,
    email: str,
    status: str,
    user_id: str | None = None,
    ip_address: str | None = None,
) -> None:
    """Record a login attempt (success or failed). Uses secret key to bypass RLS."""
    try:
        client = get_supabase_admin_client()
        client.table("login_history").insert(
            {
                "user_id": user_id,
                "email": email.strip().lower() if email else None,
                "ip_address": ip_address,
                "status": status,
            }
        ).execute()
    except Exception:
        # Never block login flow if audit logging fails.
        pass


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
