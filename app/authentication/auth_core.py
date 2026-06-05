"""Auth helpers without Streamlit dependencies (testable)."""

from __future__ import annotations

from app.database.supabase_client import get_supabase_client

INVALID_CREDENTIALS = "Invalid login credentials"


def sign_in(email: str, password: str) -> dict:
    """
    Sign in with email/password.
    Returns dict with keys: ok, user_id, email, error.
    """
    email = email.strip().lower()
    if not email or not password:
        return {"ok": False, "error": "Email and password are required."}

    client = get_supabase_client()
    try:
        response = client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as exc:
        message = str(exc)
        if INVALID_CREDENTIALS.lower() in message.lower():
            return {
                "ok": False,
                "error": INVALID_CREDENTIALS,
                "hint": (
                    "Test accounts may not be seeded yet. Restart the app after setting "
                    "SUPABASE_SECRET_KEY, or run: python scripts/validate_auth.py"
                ),
            }
        return {"ok": False, "error": message}

    if not response.user:
        return {"ok": False, "error": "Login failed: no user returned."}

    return {
        "ok": True,
        "user_id": response.user.id,
        "email": response.user.email,
        "user": response.user,
        "session": response.session,
    }
