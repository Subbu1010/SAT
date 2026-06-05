from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd

from app.database.supabase_client import get_supabase_client


def _fetch_attempts_with_questions(user_id: str) -> list[dict]:
    result = (
        get_supabase_client()
        .table("practice_attempts")
        .select(
            "is_correct, time_spent, created_at, questions(topic, subject, difficulty)"
        )
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def _fetch_mock_exams(user_id: str) -> list[dict]:
    result = (
        get_supabase_client()
        .table("mock_exams")
        .select("score, accuracy, duration, completed_at, subject_breakdown")
        .eq("user_id", user_id)
        .order("completed_at", desc=True)
        .execute()
    )
    return result.data or []


def _aggregate_by_field(attempts: list[dict], field: str) -> pd.DataFrame:
    stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"correct": 0, "total": 0, "time_spent": 0}
    )

    for row in attempts:
        question = row.get("questions") or {}
        key = question.get(field) or "Unknown"
        stats[key]["total"] += 1
        if row.get("is_correct"):
            stats[key]["correct"] += 1
        stats[key]["time_spent"] += row.get("time_spent") or 0

    rows = []
    for key, values in sorted(stats.items()):
        total = values["total"]
        rows.append(
            {
                field: key,
                "accuracy": round(values["correct"] / total * 100, 1) if total else 0.0,
                "time_spent": round(values["time_spent"] / total) if total else 0,
                "attempts": total,
            }
        )
    return pd.DataFrame(rows)


def get_performance_analytics(user_id: str) -> dict[str, Any]:
    attempts = _fetch_attempts_with_questions(user_id)
    exams = _fetch_mock_exams(user_id)

    topic_perf = _aggregate_by_field(attempts, "topic")
    subject_perf = _aggregate_by_field(attempts, "subject")
    difficulty_perf = _aggregate_by_field(attempts, "difficulty")

    exam_rows = []
    for index, exam in enumerate(reversed(exams)):
        exam_rows.append(
            {
                "exam": f"Exam {index + 1}",
                "score": exam.get("score"),
                "accuracy": float(exam.get("accuracy") or 0),
                "completed_at": exam.get("completed_at"),
            }
        )
    exam_history = pd.DataFrame(exam_rows)

    return {
        "topic_performance": topic_perf,
        "subject_performance": subject_perf,
        "difficulty_performance": difficulty_perf,
        "exam_history": exam_history,
        "total_attempts": len(attempts),
        "total_exams": len(exams),
        "has_data": bool(attempts or exams),
    }
