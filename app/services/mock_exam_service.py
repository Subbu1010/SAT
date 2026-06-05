from __future__ import annotations

import random
import time
from typing import Any

from app.database.supabase_client import get_supabase_client
from app.services.question_service import QuestionService
from app.utils.question_shuffle import shuffle_question_choices, shuffle_questions

SUBJECTS = ["Math", "Reading", "Writing"]
DEFAULT_QUESTIONS_PER_SUBJECT = 10

EXAM_SCORE_CONFIG: dict[str, dict[str, int]] = {
    "SAT": {"min": 400, "max": 1600},
    "PSAT": {"min": 320, "max": 1520},
    "PSAT 8/9": {"min": 240, "max": 1440},
}


def _exam_score_config(exam_type: str) -> dict[str, int]:
    return EXAM_SCORE_CONFIG.get(exam_type, EXAM_SCORE_CONFIG["SAT"])


def build_mock_exam(
    exam_type: str,
    questions_per_subject: int = DEFAULT_QUESTIONS_PER_SUBJECT,
) -> list[dict]:
    """Assemble a balanced mock exam from the question bank."""
    qs = QuestionService()
    selected: list[dict] = []

    for subject in SUBJECTS:
        pool = qs.get_questions(exam_type=exam_type, subject=subject, limit=5000)
        if not pool:
            continue
        count = min(questions_per_subject, len(pool))
        selected.extend(random.sample(pool, count))

    return shuffle_question_choices(shuffle_questions(selected))


def _normalize_answer(value: str | int | float | None) -> str | None:
    if value is None:
        return None
    return str(value).strip()


def _question_status(selected: str | None, correct_answer: str | None) -> str:
    selected_norm = _normalize_answer(selected)
    correct_norm = _normalize_answer(correct_answer)
    if not selected_norm:
        return "unanswered"
    if selected_norm == correct_norm:
        return "correct"
    return "incorrect"


def score_exam(
    questions: list[dict],
    answers: dict[str, str],
    exam_type: str = "SAT",
) -> dict[str, Any]:
    correct = 0
    incorrect = 0
    unanswered = 0
    subject_stats: dict[str, dict[str, int]] = {}
    topic_stats: dict[str, dict[str, int]] = {}
    question_review: list[dict[str, Any]] = []

    total = len(questions)
    score_cfg = _exam_score_config(exam_type)
    score_range = score_cfg["max"] - score_cfg["min"]
    sat_per_question_max = round(score_range / total) if total else 0

    for index, question in enumerate(questions):
        qid = question["question_id"]
        subject = question.get("subject", "Unknown")
        topic = question.get("topic", "Unknown")
        selected = answers.get(qid)
        correct_answer = question.get("answer")
        status = _question_status(selected, correct_answer)
        is_correct = status == "correct"

        if status == "correct":
            correct += 1
        elif status == "incorrect":
            incorrect += 1
        else:
            unanswered += 1

        subject_stats.setdefault(
            subject,
            {"correct": 0, "total": 0, "sat_earned": 0, "sat_possible": 0},
        )
        subject_stats[subject]["total"] += 1
        subject_stats[subject]["sat_possible"] += sat_per_question_max
        if is_correct:
            subject_stats[subject]["correct"] += 1
            subject_stats[subject]["sat_earned"] += sat_per_question_max

        topic_stats.setdefault(topic, {"correct": 0, "total": 0})
        topic_stats[topic]["total"] += 1
        if is_correct:
            topic_stats[topic]["correct"] += 1

        points_earned = 1 if is_correct else 0
        sat_earned = sat_per_question_max if is_correct else 0
        question_review.append(
            {
                "number": index + 1,
                "question_id": qid,
                "status": status,
                "is_correct": is_correct,
                "selected": selected,
                "correct_answer": correct_answer,
                "question_text": question.get("question_text", ""),
                "explanation": question.get("explanation", ""),
                "strategy_tip": question.get("strategy_tip", ""),
                "subject": subject,
                "topic": topic,
                "difficulty": question.get("difficulty", ""),
                "options": question.get("options", []),
                "points_earned": points_earned,
                "points_possible": 1,
                "sat_earned": sat_earned,
                "sat_possible": sat_per_question_max,
            }
        )

    total_points = total
    raw_score = correct
    accuracy = round(correct / total * 100, 1) if total else 0.0
    sat_earned_total = correct * sat_per_question_max
    sat_possible_total = total * sat_per_question_max
    composite_score = score_cfg["min"] + sat_earned_total

    return {
        "correct": correct,
        "incorrect": incorrect,
        "unanswered": unanswered,
        "total": total,
        "raw_score": raw_score,
        "total_points": total_points,
        "accuracy": accuracy,
        "score": sat_earned_total,
        "composite_score": composite_score,
        "sat_earned_total": sat_earned_total,
        "sat_possible_total": sat_possible_total,
        "score_min": score_cfg["min"],
        "score_max": score_cfg["max"],
        "sat_per_question_max": sat_per_question_max,
        "exam_type": exam_type,
        "subject_breakdown": subject_stats,
        "topic_breakdown": topic_stats,
        "question_review": question_review,
    }


def _subject_breakdown_for_save(results: dict[str, Any]) -> dict[str, Any]:
    breakdown = dict(results.get("subject_breakdown") or {})
    breakdown["__summary__"] = {
        "questions_answered": results.get("correct", 0) + results.get("incorrect", 0),
        "questions_total": results.get("total", 0),
    }
    return breakdown


def save_mock_exam(
    user_id: str,
    results: dict[str, Any],
    duration_seconds: int,
) -> None:
    payload = {
        "user_id": user_id,
        "score": results["score"],
        "accuracy": results["accuracy"],
        "duration": duration_seconds,
        "subject_breakdown": _subject_breakdown_for_save(results),
        "topic_breakdown": results["topic_breakdown"],
    }
    get_supabase_client().table("mock_exams").insert(payload).execute()


def elapsed_seconds(start_ts: float, end_ts: float | None = None) -> int:
    return max(0, int((end_ts or time.time()) - start_ts))
