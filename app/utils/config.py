import os
from dataclasses import dataclass
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# Load .env from project root reliably, regardless of launch directory.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Override stale host env vars so local/repo .env stays authoritative in dev.
load_dotenv(PROJECT_ROOT / ".env", override=True)


def _strip_quotes(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _app_env() -> str:
    return _strip_quotes(os.environ.get("APP_ENV")) or "development"


def _from_secrets(key: str) -> str | None:
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return _strip_quotes(str(st.secrets[key]))
    except Exception:
        pass
    return None


def _from_secret_or_env(key: str, default: str | None = None) -> str | None:
    env_value = _strip_quotes(os.environ.get(key))

    # Local dev: .env (loaded above) wins over Streamlit's cached secrets snapshot.
    if _app_env() == "development":
        if env_value:
            return env_value
        secret_value = _from_secrets(key)
        if secret_value:
            return secret_value
        return default

    # Production / Streamlit Cloud: explicit secrets.toml wins.
    secret_value = _from_secrets(key)
    if secret_value:
        return secret_value
    if env_value:
        return env_value
    return default


def supabase_key_fingerprint() -> str:
    """Masked publishable key prefix for auth troubleshooting."""
    publishable = _first_set("SUPABASE_PUBLISHABLE_KEY", "SUPABASE_KEY") or ""
    if not publishable:
        return "<missing publishable key>"
    if len(publishable) <= 16:
        return "*" * len(publishable)
    return f"{publishable[:14]}...{publishable[-6:]}"


def _first_set(*keys: str) -> str | None:
    for key in keys:
        value = _from_secret_or_env(key)
        if value:
            return value
    return None


@dataclass(frozen=True)
class AppConfig:
    supabase_url: str
    supabase_publishable_key: str
    supabase_secret_key: str | None
    supabase_db_url: str | None
    gemini_api_key: str | None
    gemini_base_url: str
    gemini_model: str
    app_env: str

    @property
    def supabase_key(self) -> str:
        """Alias used by app client (publishable/anon key)."""
        return self.supabase_publishable_key

    @property
    def supabase_service_role_key(self) -> str | None:
        """Alias used by admin/seed operations (secret/service role key)."""
        return self.supabase_secret_key

    @property
    def openai_base_url(self) -> str:
        """Backward-compatible alias for older modules."""
        return self.gemini_base_url

    @property
    def openai_model(self) -> str:
        """Backward-compatible alias for older modules."""
        return self.gemini_model


def get_config() -> AppConfig:
    supabase_url = _first_set("SUPABASE_URL")
    publishable = _first_set("SUPABASE_PUBLISHABLE_KEY", "SUPABASE_KEY")
    secret = _first_set("SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not publishable:
        raise RuntimeError(
            "Missing Supabase API credentials. Set SUPABASE_URL and "
            "SUPABASE_PUBLISHABLE_KEY (or SUPABASE_KEY) in .env / Streamlit secrets."
        )

    return AppConfig(
        supabase_url=supabase_url,
        supabase_publishable_key=publishable,
        supabase_secret_key=secret,
        supabase_db_url=_from_secret_or_env("SUPABASE_DB_URL"),
        gemini_api_key=_from_secret_or_env("GEMINI_API_KEY"),
        gemini_base_url=_first_set(
            "GEMINI_BASE_URL",
            "OPENAI_BASE_URL",
        )
        or "https://generativelanguage.googleapis.com/v1beta/openai/",
        # Gemini-only default model.
        # OPENAI_MODEL is kept as a backward-compatible alias for existing .env files.
        gemini_model=_first_set("GEMINI_MODEL", "OPENAI_MODEL") or "gemini-2.5-flash-lite",
        app_env=_from_secret_or_env("APP_ENV", "development") or "development",
    )
