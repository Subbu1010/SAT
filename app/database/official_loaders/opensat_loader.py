"""Load digital SAT-style questions from the OpenSAT public JSON database."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from app.database.official_loaders.validation import (
    dedupe_rows,
    dedupe_source_items,
    exam_types_for_question,
    is_valid_question_row,
    is_valid_source_item,
)

OPENSAT_SOURCE = "opensat_community"
OPENSAT_JSON_URL = "https://api.jsonsilo.com/public/942c3c3b-3a0c-4be3-81c2-12029def19f5"
USER_AGENT = "SAT-Adaptive-Learning-Platform/1.0 (+educational; opensat attribution)"

MATH_DOMAIN_TOPIC = {
    "Algebra": "Algebra",
    "Advanced Math": "Advanced Math",
    "Problem-Solving and Data Analysis": "Problem Solving",
    "Geometry and Trigonometry": "Geometry",
}

WRITING_GRAMMAR_DOMAINS = {"Standard English Conventions"}
WRITING_RHETORIC_DOMAINS = {"Expression of Ideas"}


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "null":
        return None
    return text


def _math_topic(domain: str, question_text: str, index: int) -> str:
    if domain == "Problem-Solving and Data Analysis":
        return "Data Analysis" if index % 2 else "Problem Solving"
    if domain == "Geometry and Trigonometry":
        lowered = question_text.lower()
        if any(token in lowered for token in ("sin", "cos", "tan", "trigon", "radian")):
            return "Trigonometry"
        return "Geometry" if index % 2 else "Trigonometry"
    return MATH_DOMAIN_TOPIC.get(domain, "Algebra")


def _english_subject_topic(domain: str, question_text: str) -> tuple[str, str]:
    if domain in WRITING_GRAMMAR_DOMAINS:
        return "Writing", "Grammar"
    if domain in WRITING_RHETORIC_DOMAINS:
        return "Writing", "Writing"
    if domain == "Craft and Structure" and re.search(
        r"most nearly means|most closely means|as used in",
        question_text,
        re.I,
    ):
        return "Reading", "Vocabulary"
    return "Reading", "Reading Comprehension"


def _choices_list(choices: dict[str, str]) -> list[str]:
    ordered_keys = sorted(choices.keys())
    return [choices[key].strip() for key in ordered_keys if choices.get(key)]


def _answer_text(choices: dict[str, str], correct: str) -> str:
    correct = correct.strip().upper()
    if correct in choices:
        return choices[correct].strip()
    if correct in choices.values():
        return correct
    return correct


def _normalize_row(
    *,
    exam_type: str,
    subject: str,
    topic: str,
    difficulty: str,
    skill_category: str,
    question_text: str,
    options: list[str],
    answer: str,
    explanation: str,
    passage: str | None,
    estimated_time: int,
) -> dict[str, Any]:
    return {
        "exam_type": exam_type,
        "subject": subject,
        "topic": topic,
        "difficulty": difficulty,
        "skill_category": skill_category,
        "question_text": question_text,
        "passage": passage,
        "options": options,
        "answer": answer,
        "explanation": explanation,
        "strategy_tip": "Eliminate choices that contradict the passage or math setup.",
        "estimated_time": estimated_time,
        "source": OPENSAT_SOURCE,
    }


def _transform_math_item(item: dict[str, Any], index: int) -> list[dict[str, Any]]:
    payload = item.get("question") or {}
    choices = payload.get("choices") or {}
    question_text = _clean(payload.get("question"))
    if not question_text or not choices:
        return []

    options = _choices_list(choices)
    answer = _answer_text(choices, str(payload.get("correct_answer", "")))
    if not options or not answer:
        return []

    difficulty = _clean(item.get("difficulty")) or "Medium"
    domain = _clean(item.get("domain")) or "Algebra"
    topic = _math_topic(domain, question_text, index)
    explanation = _clean(payload.get("explanation")) or ""
    estimated_time = 55 if difficulty == "Easy" else 70 if difficulty == "Hard" else 60

    rows = []
    for exam_type in exam_types_for_question(difficulty):
        row = _normalize_row(
            exam_type=exam_type,
            subject="Math",
            topic=topic,
            difficulty=difficulty,
            skill_category=domain,
            question_text=question_text,
            options=options,
            answer=answer,
            explanation=explanation,
            passage=None,
            estimated_time=estimated_time,
        )
        if is_valid_question_row(row):
            rows.append(row)
    return rows


def _transform_english_item(item: dict[str, Any], index: int) -> list[dict[str, Any]]:
    payload = item.get("question") or {}
    choices = payload.get("choices") or {}
    stem = _clean(payload.get("question"))
    paragraph = _clean(payload.get("paragraph"))
    if not stem or not choices:
        return []

    options = _choices_list(choices)
    answer = _answer_text(choices, str(payload.get("correct_answer", "")))
    if not options or not answer:
        return []

    difficulty = _clean(item.get("difficulty")) or "Medium"
    domain = _clean(item.get("domain")) or "Information and Ideas"
    subject, topic = _english_subject_topic(domain, stem)
    explanation = _clean(payload.get("explanation")) or ""
    estimated_time = 65 if difficulty == "Easy" else 80 if difficulty == "Hard" else 70

    rows = []
    for exam_type in exam_types_for_question(difficulty):
        row = _normalize_row(
            exam_type=exam_type,
            subject=subject,
            topic=topic,
            difficulty=difficulty,
            skill_category=domain,
            question_text=stem,
            options=options,
            answer=answer,
            explanation=explanation,
            passage=paragraph,
            estimated_time=estimated_time,
        )
        if is_valid_question_row(row):
            rows.append(row)
    return rows


def fetch_opensat_data() -> dict[str, list[dict[str, Any]]]:
    request = urllib.request.Request(OPENSAT_JSON_URL, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not download OpenSAT question bank: {exc}") from exc


def build_opensat_questions() -> tuple[list[dict[str, Any]], dict[str, int]]:
    data = fetch_opensat_data()
    stats = {
        "source_math": len(data.get("math") or []),
        "source_english": len(data.get("english") or []),
        "source_duplicates_removed": 0,
        "source_invalid_removed": 0,
        "row_duplicates_removed": 0,
        "row_invalid_removed": 0,
    }

    math_raw = data.get("math") or []
    english_raw = data.get("english") or []
    valid_math = [item for item in math_raw if is_valid_source_item(item, "math")]
    valid_english = [item for item in english_raw if is_valid_source_item(item, "english")]
    math_items, math_dupes = dedupe_source_items(valid_math)
    english_items, english_dupes = dedupe_source_items(valid_english)

    stats["source_invalid_removed"] = (len(math_raw) - len(valid_math)) + (
        len(english_raw) - len(valid_english)
    )
    stats["source_duplicates_removed"] = math_dupes + english_dupes

    rows: list[dict[str, Any]] = []
    for index, item in enumerate(math_items):
        rows.extend(_transform_math_item(item, index))
    for index, item in enumerate(english_items):
        rows.extend(_transform_english_item(item, index))

    rows, row_dupes = dedupe_rows(rows)
    stats["row_duplicates_removed"] = row_dupes
    stats["loaded"] = len(rows)
    return rows, stats
