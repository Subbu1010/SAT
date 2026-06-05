"""Shared metadata for the exam-style practice catalog."""

from __future__ import annotations

EXAM_CATALOG_SOURCE = "exam_catalog"
EXAM_TYPES = ["SAT", "PSAT", "PSAT 8/9"]
SUBJECT_TOPICS: dict[str, list[str]] = {
    "Math": [
        "Algebra",
        "Advanced Math",
        "Problem Solving",
        "Data Analysis",
        "Geometry",
        "Trigonometry",
    ],
    "Reading": ["Reading Comprehension", "Vocabulary"],
    "Writing": ["Grammar", "Writing"],
}
QUESTIONS_PER_GROUP = 100

DIFFICULTY_ORDER = ["Easy", "Medium", "Hard"]
DIFFICULTY_PATTERN = {
    "PSAT 8/9": ["Easy", "Easy", "Medium", "Easy", "Medium", "Easy", "Medium", "Hard"],
    "PSAT": ["Easy", "Medium", "Easy", "Medium", "Hard", "Medium"],
    "SAT": ["Easy", "Medium", "Hard"],
}
