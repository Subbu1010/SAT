"""Exam-style question catalog for SAT, PSAT, and PSAT 8/9."""

from app.database.exam_catalog.constants import (
    EXAM_CATALOG_SOURCE,
    EXAM_TYPES,
    QUESTIONS_PER_GROUP,
    SUBJECT_TOPICS,
)
from app.database.exam_catalog.generators import generate_group


def group_keys() -> list[tuple[str, str, str]]:
    keys: list[tuple[str, str, str]] = []
    for exam_type in EXAM_TYPES:
        for subject, topics in SUBJECT_TOPICS.items():
            for topic in topics:
                keys.append((exam_type, subject, topic))
    return keys


__all__ = [
    "EXAM_CATALOG_SOURCE",
    "EXAM_TYPES",
    "QUESTIONS_PER_GROUP",
    "SUBJECT_TOPICS",
    "generate_group",
    "group_keys",
]
