from __future__ import annotations

from app.database.supabase_client import get_supabase_admin_client
from app.utils.config import get_config


def _find_auth_user_id(client, email: str) -> str | None:
    try:
        listed = client.auth.admin.list_users()
        users = getattr(listed, "users", listed)
        for user in users:
            if getattr(user, "email", "").lower() == email.lower():
                return user.id
    except Exception:
        pass
    return None


def create_user(
    email: str,
    first_name: str,
    last_name: str,
    role: str,
    password: str,
) -> tuple[bool, str]:
    """
    Create Supabase Auth user + public.users row (admin API).
    Returns (success, message).
    """
    cfg = get_config()
    if not cfg.supabase_secret_key:
        return False, "SUPABASE_SECRET_KEY is required for admin user creation."

    email = email.strip().lower()
    first_name = first_name.strip()
    last_name = last_name.strip()
    if not email or not first_name or not last_name or not password:
        return False, "Email, first name, last name, and password are required."

    if role not in {"admin", "teacher", "student"}:
        return False, "Invalid role."

    client = get_supabase_admin_client()
    metadata = {"first_name": first_name, "last_name": last_name, "role": role}

    try:
        existing_id = _find_auth_user_id(client, email)
        if existing_id:
            client.auth.admin.update_user_by_id(
                existing_id,
                {
                    "password": password,
                    "email_confirm": True,
                    "user_metadata": metadata,
                },
            )
            user_id = existing_id
            created = False
        else:
            auth_resp = client.auth.admin.create_user(
                {
                    "email": email,
                    "password": password,
                    "email_confirm": True,
                    "user_metadata": metadata,
                }
            )
            user_id = auth_resp.user.id
            created = True

        client.table("users").upsert(
            {
                "user_id": user_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "role": role,
                "is_disabled": False,
            },
            on_conflict="user_id",
        ).execute()

        if role == "student":
            profile = (
                client.table("student_profiles")
                .select("profile_id")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            if not profile.data:
                client.table("student_profiles").insert(
                    {"user_id": user_id, "grade": "", "target_score": None}
                ).execute()

        action = "created" if created else "updated"
        return True, f"User {action}: {email} ({role})"
    except Exception as exc:
        return False, str(exc)
