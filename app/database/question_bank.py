"""Backward-compatible re-exports for the exam question catalog."""

from app.database.exam_catalog import (
    EXAM_CATALOG_SOURCE as BULK_SOURCE,
    EXAM_TYPES,
    QUESTIONS_PER_GROUP,
    SUBJECT_TOPICS,
    generate_group,
    group_keys,
)

__all__ = [
    "BULK_SOURCE",
    "EXAM_TYPES",
    "QUESTIONS_PER_GROUP",
    "SUBJECT_TOPICS",
    "generate_group",
    "group_keys",
]
