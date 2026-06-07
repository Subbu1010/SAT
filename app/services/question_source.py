from __future__ import annotations

import re
from datetime import datetime

from app.database.official_loaders.bluebook_loader import BLUEBOOK_SOURCE
from app.database.official_loaders.opensat_loader import OPENSAT_SOURCE
from app.utils.datetime_display import CST, parse_timestamp

IMPORT_SOURCE_PREFIX = "import:"
BATCH_DATE_PATTERN = re.compile(r"^.+-\d{2}/\d{2}/\d{4}$")

OFFICIAL_QUESTION_SOURCES = frozenset({OPENSAT_SOURCE, BLUEBOOK_SOURCE})

LEGACY_SOURCE_LABELS = {
    OPENSAT_SOURCE: "OpenSAT",
    BLUEBOOK_SOURCE: "Bluebook",
}


def normalize_source_name(name: str) -> str:
    text = re.sub(r"[^\w\s]", "", str(name).strip())
    parts = [part for part in re.split(r"\s+", text) if part]
    return "".join(part[:1].upper() + part[1:] for part in parts)


def format_batch_name(source_name: str, *, on_date: datetime | None = None) -> str:
    """Build a batch label: Source-MM/DD/YYYY (e.g. CollegeBoard-01/25/2026)."""
    normalized = normalize_source_name(source_name)
    if not normalized:
        raise ValueError("Source name is required.")
    batch_date = on_date or datetime.now(CST)
    if batch_date.tzinfo is None:
        batch_date = batch_date.replace(tzinfo=CST)
    else:
        batch_date = batch_date.astimezone(CST)
    return f"{normalized}-{batch_date.strftime('%m/%d/%Y')}"


def is_dated_batch_source(source: str | None) -> bool:
    if not source:
        return False
    if source.startswith(IMPORT_SOURCE_PREFIX):
        return True
    return bool(BATCH_DATE_PATTERN.match(source))


def is_admin_batch_source(source: str | None) -> bool:
    if not source or source in OFFICIAL_QUESTION_SOURCES:
        return False
    return is_dated_batch_source(source)


def is_import_source(source: str | None) -> bool:
    """Backward-compatible alias for admin-upload batch labels."""
    return is_admin_batch_source(source)


def display_batch_label(source: str | None, loaded_at: datetime | str | None = None) -> str:
    """Format any stored source value for student-facing batch display."""
    if not source:
        return format_batch_name("OpenSAT")

    if is_dated_batch_source(source):
        return source

    legacy_name = LEGACY_SOURCE_LABELS.get(source)
    if legacy_name:
        loaded_dt = parse_timestamp(loaded_at) or datetime.now(CST)
        return format_batch_name(legacy_name, on_date=loaded_dt)

    return source
