from __future__ import annotations

import streamlit as st
from supabase import Client

from app.database.bulk_seed import exam_bank_ready, reload_exam_catalog, seed_bulk_questions
from app.database.exam_catalog import EXAM_TYPES
from app.database.seed_data import DEFAULT_TEST_PASSWORD, TEST_USERS
from app.database.supabase_client import get_supabase_admin_client, get_supabase_client
from app.utils.config import get_config

_SECRET_KEY_HINT = "Set SUPABASE_SECRET_KEY (or SUPABASE_SERVICE_ROLE_KEY) in .env."
_SCHEMA_HINT = "Run app/database/schema.sql once in Supabase SQL Editor first."


def _admin_client() -> Client | None:
    cfg = get_config()
    if not cfg.supabase_secret_key:
        return None
    try:
        return get_supabase_admin_client()
    except Exception:
        return None


def _user_id_for_email(client: Client, email: str) -> str | None:
    """Fast lookup from public.users (avoids slow auth.admin.list_users)."""
    row = client.table("users").select("user_id").eq("email", email).limit(1).execute()
    if row.data:
        return row.data[0]["user_id"]
    return None


def _ensure_auth_user(client: Client, user: dict) -> tuple[str, bool]:
    """Create auth user if missing; returns (user_id, was_created)."""
    email = user["email"]
    metadata = {
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "role": user["role"],
    }

    existing_id = _user_id_for_email(client, email)
    if existing_id:
        return existing_id, False

    auth_resp = client.auth.admin.create_user(
        {
            "email": email,
            "password": DEFAULT_TEST_PASSWORD,
            "email_confirm": True,
            "user_metadata": metadata,
        }
    )
    return auth_resp.user.id, True


def seed_test_users() -> tuple[bool, str]:
    client = _admin_client()
    if client is None:
        return False, f"User seed skipped: {_SECRET_KEY_HINT}"

    test_emails = [u["email"] for u in TEST_USERS]
    try:
        existing = client.table("users").select("email").in_("email", test_emails).execute()
        if len(existing.data or []) >= len(TEST_USERS):
            return True, "Test users already loaded."
    except Exception as exc:
        if "relation" in str(exc).lower() or "does not exist" in str(exc).lower():
            return False, f"User seed failed: tables missing. {_SCHEMA_HINT}"
        return False, f"User seed failed: {exc}"

    created = 0
    for user in TEST_USERS:
        email = user["email"]
        try:
            user_id, was_created = _ensure_auth_user(client, user)
            if was_created:
                created += 1
        except Exception as exc:
            if "already" in str(exc).lower():
                user_id = _user_id_for_email(client, email)
                if not user_id:
                    return False, f"User seed failed for {email}: {exc}"
            elif "relation" in str(exc).lower() or "does not exist" in str(exc).lower():
                return False, f"User seed failed: tables missing. {_SCHEMA_HINT}"
            else:
                return False, f"User seed failed for {email}: {exc}"

        client.table("users").upsert(
            {
                "user_id": user_id,
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "email": email,
                "role": user["role"],
                "is_disabled": False,
            },
            on_conflict="user_id",
        ).execute()

        if user["role"] == "student":
            profile = (
                client.table("student_profiles").select("profile_id").eq("user_id", user_id).execute()
            )
            if not profile.data:
                client.table("student_profiles").insert(
                    {"user_id": user_id, "grade": "11", "target_score": 1400}
                ).execute()

    return True, (
        f"Test users ready ({created} new). Password: {DEFAULT_TEST_PASSWORD}"
    )


def seed_sample_questions() -> tuple[bool, str]:
    """Legacy sample seed disabled — full exam catalog is used instead."""
    return True, "Sample question seed skipped (exam catalog is the sole question source)."


def seed_practice_bank() -> tuple[bool, str]:
    """Ensure SAT, PSAT, and PSAT 8/9 banks are populated from the OpenSAT source."""
    if st.session_state.get("_practice_bank_ready"):
        return True, f"Practice bank ready for {', '.join(EXAM_TYPES)}."

    if exam_bank_ready():
        st.session_state["_practice_bank_ready"] = True
        return True, f"Practice bank ready for {', '.join(EXAM_TYPES)}."

    ok, message = seed_bulk_questions()
    if ok and exam_bank_ready(min_per_exam=200):
        st.session_state["_practice_bank_ready"] = True
        return True, f"Loaded practice questions for {', '.join(EXAM_TYPES)}. {message}"
    return ok, message


def run_startup_seed() -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []

    user_ok, user_msg = seed_test_users()
    results.append(("success" if user_ok else "info", user_msg))

    q_ok, q_msg = seed_sample_questions()
    results.append(("success" if q_ok else "warning", q_msg))

    bank_ok, bank_msg = seed_practice_bank()
    results.append(("success" if bank_ok else "warning", bank_msg))

    return results
