"""Resolve the connected client's IP address and approximate location."""

from __future__ import annotations

import ipaddress
import json
import urllib.error
import urllib.request

import streamlit as st

_GEO_CACHE_PREFIX = "_client_geo_"
_LOOKUP_TIMEOUT_SEC = 0.4
_LOCAL_IP_LABEL = "localhost"
_LOCAL_LOCATION = "Local / unknown"


def _ip_from_headers() -> str | None:
    """Read client IP from reverse-proxy headers when Streamlit context has none."""
    headers = st.context.headers
    for header in ("X-Forwarded-For", "X-Real-Ip", "Cf-Connecting-Ip"):
        raw: str | None = None
        try:
            raw = headers[header]
        except KeyError:
            try:
                values = headers.get_all(header)
                raw = values[0] if values else None
            except (KeyError, AttributeError):
                continue
        if not raw:
            continue
        candidate = raw.split(",")[0].strip()
        if candidate and candidate not in {"::1", "127.0.0.1"}:
            return candidate
    return None


def get_client_ip() -> str | None:
    """Return the best available client IP, or None when only localhost is visible."""
    ip = st.context.ip_address
    if ip and ip not in {"::1", "127.0.0.1"}:
        return ip
    return _ip_from_headers()


def _audit_ip_label(ip: str | None) -> str:
    """Stable value stored in login history so local dev is not blank."""
    return ip or _LOCAL_IP_LABEL


def _is_private_or_local_ip(ip: str) -> bool:
    if ip == _LOCAL_IP_LABEL:
        return True
    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        return False


def resolve_ip_location(ip: str | None) -> str:
    """Best-effort city/region/country lookup for a public IP address."""
    if not ip or ip == _LOCAL_IP_LABEL:
        return _LOCAL_LOCATION
    if _is_private_or_local_ip(ip):
        return "Local / private network"

    cache_key = f"{_GEO_CACHE_PREFIX}{ip}"
    if cache_key in st.session_state:
        cached = st.session_state[cache_key]
        return cached or "Unknown"

    location = _lookup_ip_location(ip) or "Unknown"
    st.session_state[cache_key] = location
    return location


def _lookup_ip_location(ip: str) -> str | None:
    url = f"https://ipapi.co/{ip}/json/"
    request = urllib.request.Request(url, headers={"User-Agent": "SAT-App/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=_LOOKUP_TIMEOUT_SEC) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None

    if payload.get("error"):
        return None

    parts = [
        value
        for value in (
            payload.get("city"),
            payload.get("region"),
            payload.get("country_name"),
        )
        if value
    ]
    return ", ".join(parts) if parts else None


def get_client_audit_info(*, resolve_location: bool = True) -> tuple[str, str]:
    """IP and location tuple for security audit logging."""
    ip = get_client_ip()
    labeled_ip = _audit_ip_label(ip)
    if not resolve_location:
        return labeled_ip, "Unknown"
    return labeled_ip, resolve_ip_location(ip)
