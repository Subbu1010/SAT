from __future__ import annotations

from datetime import datetime

import streamlit as st

from app.authentication.auth_core import sign_in
from app.authentication.session_store import (
    clear_session_tokens,
    restore_session,
    save_session_tokens,
)
from app.database.supabase_client import get_supabase_admin_client, get_supabase_client
from app.services.login_history_service import log_login_event
from app.utils.client_info import get_client_audit_info
from app.utils.user_session import clear_user_session_state, ensure_user_session_scope

_USER_ROLE_KEY = "auth_user_role"


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

    def _log_audit_event(
        self,
        *,
        email: str,
        status: str,
        user_id: str | None = None,
    ) -> None:
        ip_address, location = get_client_audit_info(resolve_location=False)
        log_login_event(
            email=email,
            status=status,
            user_id=user_id,
            ip_address=ip_address,
            location=location,
        )

    def login(self, email: str, password: str, remember_me: bool = False):
        result = sign_in(email, password)
        if not result["ok"]:
            self._log_audit_event(email=email, status="failed")
            hint = result.get("hint", "")
            raise RuntimeError(f"{result['error']}. {hint}".strip())

        user = result["user"]
        if self._is_user_disabled(user.id):
            self._log_audit_event(
                user_id=user.id,
                email=result.get("email") or email,
                status="disabled",
            )
            raise RuntimeError(
                "This account has been disabled. Contact your administrator."
            )

        self._log_audit_event(
            user_id=user.id,
            email=result.get("email") or email,
            status="success",
        )
        session = result.get("session")
        st.session_state["auth_user"] = user
        st.session_state["is_authenticated"] = True
        st.session_state["session_persistent"] = remember_me
        meta = user.user_metadata or {}
        st.session_state[_USER_ROLE_KEY] = meta.get("role", "student")

        if session:
            self._apply_session(session)
            save_session_tokens(session, remember_me)

        ensure_user_session_scope(user.id)

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

    def _is_user_disabled(self, user_id: str) -> bool:
        try:
            admin = get_supabase_admin_client()
            row = (
                admin.table("users")
                .select("is_disabled")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            return bool(row.data and row.data[0].get("is_disabled"))
        except Exception:
            return False

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
            },
            on_conflict="user_id",
        ).execute()
        if self.current_user() and self.current_user().id == user_id:
            st.session_state[_USER_ROLE_KEY] = role

    def logout(self):
        user = self.current_user()
        if user:
            self._log_audit_event(
                user_id=user.id,
                email=user.email or "",
                status="logout",
            )
        try:
            self.client.auth.sign_out()
        except Exception:
            pass
        clear_session_tokens()
        clear_user_session_state()
        st.session_state.pop("auth_user", None)
        st.session_state["is_authenticated"] = False
        st.session_state.pop("session_persistent", None)
        st.session_state.pop("auth_access_token", None)
        st.session_state.pop("auth_refresh_token", None)
        st.session_state.pop("active_user_id", None)
        st.session_state.pop(_USER_ROLE_KEY, None)

    def forgot_password(self, email: str):
        return self.client.auth.reset_password_for_email(email.strip())

    def must_reset_password(self) -> bool:
        user = self.current_user()
        if not user:
            return False
        return bool((user.user_metadata or {}).get("must_reset_password"))

    def change_password(self, new_password: str):
        return self.client.auth.update_user({"password": new_password})

    def _apply_session(self, session) -> None:
        if not session or not getattr(session, "access_token", None):
            return
        self.client.auth.set_session(session.access_token, session.refresh_token)
        st.session_state["auth_access_token"] = session.access_token
        st.session_state["auth_refresh_token"] = session.refresh_token

    def ensure_supabase_session(self) -> bool:
        """Ensure the Supabase client has a valid JWT for auth APIs."""
        try:
            response = self.client.auth.get_user()
            if response and response.user:
                return True
        except Exception:
            pass

        access = st.session_state.get("auth_access_token")
        refresh = st.session_state.get("auth_refresh_token")
        if access and refresh:
            try:
                result = self.client.auth.set_session(access, refresh)
                if result and result.user:
                    st.session_state["auth_user"] = result.user
                if result and result.session:
                    self._apply_session(result.session)
                return bool(result and result.user)
            except Exception:
                pass

        return restore_session(self.client)

    def complete_password_reset(self, new_password: str) -> None:
        user = self.current_user()
        if not user:
            raise RuntimeError("Not logged in.")

        email = user.email or ""
        metadata = dict(user.user_metadata or {})
        metadata["must_reset_password"] = False
        update_payload = {"password": new_password, "user_metadata": metadata}

        if not self.ensure_supabase_session():
            self._admin_update_user(user.id, update_payload)
        else:
            try:
                response = self.client.auth.update_user(
                    {"password": new_password, "data": metadata}
                )
                if response and response.user:
                    st.session_state["auth_user"] = response.user
                if response and response.session:
                    self._apply_session(response.session)
            except Exception:
                self._admin_update_user(user.id, update_payload)

        if email:
            result = sign_in(email, new_password)
            if result["ok"] and result.get("session"):
                self._apply_session(result["session"])
                st.session_state["auth_user"] = result["user"]
                st.session_state["is_authenticated"] = True
                save_session_tokens(
                    result["session"],
                    st.session_state.get("session_persistent", False),
                )

    def _admin_update_user(self, user_id: str, payload: dict) -> None:
        try:
            admin = get_supabase_admin_client()
            admin.auth.admin.update_user_by_id(user_id, payload)
            refreshed = admin.auth.admin.get_user_by_id(user_id)
            if refreshed and refreshed.user:
                st.session_state["auth_user"] = refreshed.user
        except Exception as exc:
            raise RuntimeError(
                "Could not update password. SUPABASE_SECRET_KEY is required for "
                "first-login password reset when the auth session is unavailable."
            ) from exc

    def current_user(self):
        return st.session_state.get("auth_user")

    def is_logged_in(self) -> bool:
        return bool(st.session_state.get("is_authenticated") and self.current_user())

    def require_auth(self):
        if not self.is_logged_in():
            st.warning("Please login to continue.")
            st.stop()

    def get_user_role(self) -> str:
        cached_role = st.session_state.get(_USER_ROLE_KEY)
        if cached_role:
            return cached_role

        user = self.current_user()
        if not user:
            return "student"

        role = (user.user_metadata or {}).get("role", "student")
        try:
            role_row = (
                self.client.table("users").select("role").eq("user_id", user.id).limit(1).execute()
            )
            if role_row.data:
                role = role_row.data[0]["role"]
        except Exception:
            pass

        st.session_state[_USER_ROLE_KEY] = role
        return role

    def require_role(self, allowed_roles: set[str]):
        self.require_auth()
        if self.get_user_role() not in allowed_roles:
            st.error("You do not have access to this section.")
            st.stop()
