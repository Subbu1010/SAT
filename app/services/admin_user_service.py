from __future__ import annotations

from app.database.supabase_client import get_supabase_admin_client
from app.utils.config import get_config

MIN_PASSWORD_LENGTH = 8


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
    metadata = {
        "first_name": first_name,
        "last_name": last_name,
        "role": role,
        "must_reset_password": True,
    }

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
        return (
            True,
            f"User {action}: {email} ({role}). "
            "They must set a new password on first login.",
        )
    except Exception as exc:
        return False, str(exc)


def update_user(
    user_id: str,
    *,
    first_name: str,
    last_name: str,
    email: str,
    role: str,
    is_disabled: bool,
    new_password: str | None = None,
    require_password_change_on_login: bool = True,
) -> tuple[bool, str]:
    """Update profile fields in public.users and sync Supabase Auth metadata."""
    cfg = get_config()
    if not cfg.supabase_secret_key:
        return False, "SUPABASE_SECRET_KEY is required for user updates."

    first_name = first_name.strip()
    last_name = last_name.strip()
    email = email.strip().lower()
    if not first_name or not last_name or not email:
        return False, "First name, last name, and email are required."

    if role not in {"admin", "teacher", "student"}:
        return False, "Invalid role."

    if new_password is not None and len(new_password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."

    client = get_supabase_admin_client()
    try:
        user_resp = client.auth.admin.get_user_by_id(user_id)
        if not user_resp or not user_resp.user:
            return False, "User not found in Supabase Auth."

        metadata = dict(user_resp.user.user_metadata or {})
        metadata.update(
            {
                "first_name": first_name,
                "last_name": last_name,
                "role": role,
            }
        )

        auth_payload: dict = {
            "email": email,
            "user_metadata": metadata,
        }
        if is_disabled:
            auth_payload["ban_duration"] = "876000h"
        else:
            auth_payload["ban_duration"] = "none"

        if new_password:
            metadata["must_reset_password"] = require_password_change_on_login
            auth_payload["password"] = new_password
            auth_payload["user_metadata"] = metadata

        client.auth.admin.update_user_by_id(user_id, auth_payload)

        client.table("users").update(
            {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "role": role,
                "is_disabled": is_disabled,
            }
        ).eq("user_id", user_id).execute()

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

        parts = [f"Updated {email}."]
        if new_password:
            if require_password_change_on_login:
                parts.append("Password reset; user must choose a new password on next login.")
            else:
                parts.append("Password updated.")
        if is_disabled:
            parts.append("Account is disabled.")
        return True, " ".join(parts)
    except Exception as exc:
        return False, str(exc)


def reset_user_password(
    user_id: str,
    new_password: str,
    *,
    require_change_on_login: bool = True,
) -> tuple[bool, str]:
    """Set a user's password via Supabase Admin API (admin-only)."""
    cfg = get_config()
    if not cfg.supabase_secret_key:
        return False, "SUPABASE_SECRET_KEY is required for password reset."

    if len(new_password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."

    client = get_supabase_admin_client()
    try:
        user_resp = client.auth.admin.get_user_by_id(user_id)
        if not user_resp or not user_resp.user:
            return False, "User not found in Supabase Auth."

        metadata = dict(user_resp.user.user_metadata or {})
        metadata["must_reset_password"] = require_change_on_login

        client.auth.admin.update_user_by_id(
            user_id,
            {
                "password": new_password,
                "user_metadata": metadata,
            },
        )

        email = user_resp.user.email or user_id
        if require_change_on_login:
            return (
                True,
                f"Password reset for {email}. They must choose a new password on next login.",
            )
        return True, f"Password updated for {email}."
    except Exception as exc:
        return False, str(exc)
