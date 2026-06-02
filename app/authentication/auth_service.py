from __future__ import annotations

from datetime import datetime

import streamlit as st

from app.authentication.auth_core import sign_in
from app.authentication.session_store import (
    clear_session_tokens,
    restore_session,
    save_session_tokens,
)
from app.database.supabase_client import get_supabase_client


class AuthService:
    def __init__(self):
        self.client = get_supabase_client()

    def restore_from_cookies(self) -> bool:
        return restore_session(self.client)

    def register(self, email: str, password: str, first_name: str, last_name: str):
        response = self.client.auth.sign_up(
            {
                "email": email.strip(),
                "password": password,
                "options": {
                    "data": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "role": "student",
                    }
                },
            }
        )
        if response.user:
            self._sync_public_user(
                user_id=response.user.id,
                email=email.strip(),
                first_name=first_name,
                last_name=last_name,
                role="student",
            )
        return response

    def login(self, email: str, password: str, remember_me: bool = False):
        result = sign_in(email, password)
        if not result["ok"]:
            hint = result.get("hint", "")
            raise RuntimeError(f"{result['error']}. {hint}".strip())

        user = result["user"]
        session = result.get("session")
        st.session_state["auth_user"] = user
        st.session_state["is_authenticated"] = True
        st.session_state["session_persistent"] = remember_me

        if session:
            save_session_tokens(session, remember_me)

        meta = user.user_metadata or {}
        try:
            self._sync_public_user(
                user_id=user.id,
                email=result["email"],
                first_name=meta.get("first_name", "Student"),
                last_name=meta.get("last_name", "User"),
                role=meta.get("role", "student"),
            )
            self.client.table("users").update({"last_login": datetime.utcnow().isoformat()}).eq(
                "user_id", user.id
            ).execute()
        except Exception:
            pass
        return result

    def _sync_public_user(
        self, user_id: str, email: str, first_name: str, last_name: str, role: str
    ) -> None:
        self.client.table("users").upsert(
            {
                "user_id": user_id,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "role": role,
                "is_disabled": False,
            },
            on_conflict="user_id",
        ).execute()

    def logout(self):
        try:
            self.client.auth.sign_out()
        except Exception:
            pass
        clear_session_tokens()
        st.session_state.pop("auth_user", None)
        st.session_state["is_authenticated"] = False
        st.session_state.pop("session_persistent", None)

    def forgot_password(self, email: str):
        return self.client.auth.reset_password_for_email(email.strip())

    def change_password(self, new_password: str):
        return self.client.auth.update_user({"password": new_password})

    def current_user(self):
        return st.session_state.get("auth_user")

    def is_logged_in(self) -> bool:
        return bool(st.session_state.get("is_authenticated") and self.current_user())

    def require_auth(self):
        if not self.is_logged_in():
            st.warning("Please login to continue.")
            st.stop()

    def require_role(self, allowed_roles: set[str]):
        self.require_auth()
        user = self.current_user()
        role_row = (
            self.client.table("users").select("role").eq("user_id", user.id).limit(1).execute()
        )
        role = (
            role_row.data[0]["role"]
            if role_row.data
            else (user.user_metadata or {}).get("role", "student")
        )
        if role not in allowed_roles:
            st.error("You do not have access to this section.")
            st.stop()
