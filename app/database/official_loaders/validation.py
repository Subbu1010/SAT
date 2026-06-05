from __future__ import annotations

import hashlib
import json
import re
from typing import Any

ALL_EXAM_TYPES = ["PSAT 8/9", "PSAT", "SAT"]

VALID_DIFFICULTIES = {"Easy", "Medium", "Hard"}
VALID_MATH_DOMAINS = {
    "Algebra",
    "Advanced Math",
    "Problem-Solving and Data Analysis",
    "Geometry and Trigonometry",
}
VALID_ENGLISH_DOMAINS = {
    "Information and Ideas",
    "Craft and Structure",
    "Standard English Conventions",
    "Expression of Ideas",
}

PLACEHOLDER_PATTERNS = (
    r"^lorem ipsum",
    r"^test question\s*\d*$",
    r"^sample question",
    r"^placeholder",
)


def exam_types_for_question(_difficulty: str) -> list[str]:
    """Every suite exam type receives Easy, Medium, and Hard questions."""
    return list(ALL_EXAM_TYPES)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def question_fingerprint(row: dict[str, Any]) -> str:
    payload = {
        "exam_type": row.get("exam_type"),
        "question_text": _normalize_text(str(row.get("question_text", ""))),
        "answer": _normalize_text(str(row.get("answer", ""))),
        "options": [_normalize_text(str(opt)) for opt in (row.get("options") or [])],
        "passage": _normalize_text(str(row.get("passage") or "")),
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def is_valid_question_row(row: dict[str, Any]) -> bool:
    question_text = str(row.get("question_text") or "").strip()
    answer = str(row.get("answer") or "").strip()
    options = [str(opt).strip() for opt in (row.get("options") or []) if str(opt).strip()]
    explanation = str(row.get("explanation") or "").strip()
    difficulty = str(row.get("difficulty") or "").strip()
    exam_type = str(row.get("exam_type") or "").strip()
    subject = str(row.get("subject") or "").strip()

    if exam_type not in ALL_EXAM_TYPES:
        return False
    if difficulty not in VALID_DIFFICULTIES:
        return False
    if subject not in {"Math", "Reading", "Writing"}:
        return False
    if len(question_text) < 20:
        return False
    if len(explanation) < 25:
        return False
    if len(options) != 4:
        return False
    if answer not in options:
        return False
    if any(re.search(pattern, _normalize_text(question_text)) for pattern in PLACEHOLDER_PATTERNS):
        return False
    return True


def is_valid_source_item(item: dict[str, Any], section: str) -> bool:
    item_id = str(item.get("id") or "").strip()
    if not item_id:
        return False

    domain = str(item.get("domain") or "").strip()
    difficulty = str(item.get("difficulty") or "").strip()
    if difficulty not in VALID_DIFFICULTIES:
        return False

    if section == "math" and domain not in VALID_MATH_DOMAINS:
        return False
    if section == "english" and domain not in VALID_ENGLISH_DOMAINS:
        return False

    payload = item.get("question") or {}
    question_text = str(payload.get("question") or "").strip()
    choices = payload.get("choices") or {}
    correct = str(payload.get("correct_answer") or "").strip()
    explanation = str(payload.get("explanation") or "").strip()

    if len(question_text) < 20 or len(explanation) < 25:
        return False
    if not isinstance(choices, dict) or len(choices) != 4:
        return False
    if not correct:
        return False
    return True


def dedupe_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    removed = 0
    for row in rows:
        key = question_fingerprint(row)
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        unique.append(row)
    return unique, removed


def dedupe_source_items(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    removed = 0
    for item in items:
        payload = item.get("question") or {}
        source_fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "question": _normalize_text(str(payload.get("question") or "")),
                    "paragraph": _normalize_text(str(payload.get("paragraph") or "")),
                    "choices": {
                        str(key): _normalize_text(str(value))
                        for key, value in sorted((payload.get("choices") or {}).items())
                    },
                    "correct_answer": _normalize_text(str(payload.get("correct_answer") or "")),
                },
                sort_keys=True,
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest()
        if source_fingerprint in seen:
            removed += 1
            continue
        seen.add(source_fingerprint)
        unique.append(item)
    return unique, removed
