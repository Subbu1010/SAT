"""Load official Bluebook practice SAT Math MCQs from public module files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.database.official_loaders.validation import exam_types_for_question, is_valid_question_row

BLUEBOOK_SOURCE = "bluebook_official_practice"
_RAW_FILES = (
    "bluebook_raw_10_module1.js",
    "bluebook_raw_10_module2.js",
    "bluebook_raw_11_module1.js",
    "bluebook_raw_11_module2.js",
)


def _decode_js_single_quoted(value: str) -> str:
    out: list[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 1 < len(value):
            nxt = value[index + 1]
            if nxt in {"'", "\\", "$"}:
                out.append(nxt)
                index += 2
                continue
        out.append(char)
        index += 1
    return "".join(out)


def _topic_for_text(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("triangle", "circle", "angle", "graph", "coordinate")):
        return "Geometry"
    if any(token in lowered for token in ("percent", "probability", "table", "data")):
        return "Data Analysis"
    if any(token in lowered for token in ("function", "equation", "inequality", "system")):
        return "Algebra"
    return "Advanced Math"


def _rows_from_block(block: str) -> list[dict[str, Any]]:
    if "type: 'mc'" not in block or "hasFigure: true" in block or "tableData:" in block:
        return []
    text_match = re.search(r"text:\s*'((?:\\.|[^'])*)'", block, flags=re.S)
    answer_match = re.search(r"answer:\s*'([A-D])'", block)
    if not text_match or not answer_match:
        return []

    option_pairs = re.findall(
        r"\{\s*label:\s*'([A-D])',\s*text:\s*'((?:\\.|[^'])*)'\s*\}",
        block,
        flags=re.S,
    )
    if len(option_pairs) != 4:
        return []
    option_map = {label: _decode_js_single_quoted(text).strip() for label, text in option_pairs}
    answer_key = answer_match.group(1)
    answer_text = option_map.get(answer_key)
    if not answer_text:
        return []

    question_text = _decode_js_single_quoted(text_match.group(1)).strip()
    if len(question_text) < 20:
        return []

    options = [option_map[k] for k in ("A", "B", "C", "D")]
    topic = _topic_for_text(question_text)
    explanation = (
        "This official Bluebook practice item is keyed to the correct option in the source module."
    )
    rows: list[dict[str, Any]] = []
    for exam_type in exam_types_for_question("Medium"):
        row = {
            "exam_type": exam_type,
            "subject": "Math",
            "topic": topic,
            "difficulty": "Medium",
            "skill_category": "Official Practice",
            "question_text": question_text,
            "passage": None,
            "options": options,
            "answer": answer_text,
            "explanation": explanation,
            "strategy_tip": "Solve systematically and verify units/signs before selecting an answer.",
            "estimated_time": 70,
            "source": BLUEBOOK_SOURCE,
        }
        if is_valid_question_row(row):
            rows.append(row)
    return rows


def build_bluebook_questions() -> tuple[list[dict[str, Any]], dict[str, int]]:
    root = Path(__file__).resolve().parent
    rows: list[dict[str, Any]] = []
    blocks_seen = 0
    for filename in _RAW_FILES:
        path = root / filename
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        blocks = re.findall(r"\{\s*id:\s*\d+,.*?\n\s*\},", text, flags=re.S)
        blocks_seen += len(blocks)
        for block in blocks:
            rows.extend(_rows_from_block(block))
    return rows, {"bluebook_blocks_seen": blocks_seen, "bluebook_loaded": len(rows)}

