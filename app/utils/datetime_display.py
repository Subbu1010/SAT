"""Format stored UTC timestamps for display in US Central Time."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

CST = ZoneInfo("America/Chicago")
UTC = ZoneInfo("UTC")
DISPLAY_FORMAT = "%b %d, %Y %I:%M %p CST"


def parse_timestamp(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def format_cst(value: datetime | str | None) -> str:
    """Return a human-readable CST string, or empty string when value is missing."""
    dt = parse_timestamp(value)
    if dt is None:
        return ""
    return dt.astimezone(CST).strftime(DISPLAY_FORMAT)


def format_rows_for_display(rows: list[dict], datetime_columns: list[str]) -> list[dict]:
    """Copy rows and replace listed timestamp columns with CST strings."""
    formatted: list[dict] = []
    for row in rows:
        copy = dict(row)
        for column in datetime_columns:
            if column in copy and copy[column]:
                copy[column] = format_cst(copy[column])
        formatted.append(copy)
    return formatted
