from datetime import datetime

from app.database.official_loaders.opensat_loader import OPENSAT_SOURCE
from app.services.question_source import (
    display_batch_label,
    format_batch_name,
    is_admin_batch_source,
    is_import_source,
    normalize_source_name,
)
from app.utils.datetime_display import CST


def test_normalize_source_name_collapses_words():
    assert normalize_source_name("college board") == "CollegeBoard"
    assert normalize_source_name("  CollegeBoard  ") == "CollegeBoard"


def test_format_batch_name_uses_source_and_date():
    label = format_batch_name(
        "College Board",
        on_date=datetime(2026, 1, 25, 12, 0, tzinfo=CST),
    )
    assert label == "CollegeBoard-01/25/2026"


def test_format_batch_name_requires_source():
    try:
        format_batch_name("   ")
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_display_batch_label_adds_date_for_legacy_opensat():
    label = display_batch_label(
        OPENSAT_SOURCE,
        loaded_at=datetime(2026, 3, 15, 18, 0, tzinfo=CST),
    )
    assert label == "OpenSAT-03/15/2026"


def test_display_batch_label_keeps_dated_batches():
    assert display_batch_label("CollegeBoard-01/25/2026") == "CollegeBoard-01/25/2026"


def test_is_admin_batch_source_recognizes_new_and_legacy_labels():
    assert is_admin_batch_source("CollegeBoard-01/25/2026")
    assert is_admin_batch_source("import:bank:20260101T120000Z:abc123")
    assert not is_admin_batch_source("opensat_community")
    assert is_import_source("CollegeBoard-01/25/2026")
