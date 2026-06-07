from datetime import datetime
from zoneinfo import ZoneInfo

from app.utils.datetime_display import format_cst, format_rows_for_display, parse_timestamp


def test_parse_timestamp_handles_z_suffix():
    dt = parse_timestamp("2024-06-15T18:30:00Z")
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.hour == 18


def test_format_cst_converts_utc_to_central():
    utc = datetime(2024, 1, 15, 18, 0, tzinfo=ZoneInfo("UTC"))
    formatted = format_cst(utc)
    assert formatted.endswith("CST")
    assert "Jan 15, 2024" in formatted
    assert "12:00 PM" in formatted


def test_format_rows_for_display_replaces_timestamp_columns():
    rows = [{"name": "Ada", "created_at": "2024-06-15T18:30:00Z"}]
    formatted = format_rows_for_display(rows, ["created_at"])
    assert formatted[0]["name"] == "Ada"
    assert formatted[0]["created_at"].endswith("CST")
