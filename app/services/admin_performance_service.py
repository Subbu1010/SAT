from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.database.supabase_client import get_supabase_admin_client


def _fetch_users() -> list[dict]:
    rows = (
        get_supabase_admin_client()
        .table("users")
        .select("user_id, first_name, last_name, email, role")
        .order("last_name")
        .execute()
    )
    return rows.data or []


def _fetch_practice_attempts() -> list[dict]:
    rows = (
        get_supabase_admin_client()
        .table("practice_attempts")
        .select("user_id, is_correct, created_at")
        .order("created_at", desc=True)
        .execute()
    )
    return rows.data or []


def _fetch_mock_exams() -> list[dict]:
    rows = (
        get_supabase_admin_client()
        .table("mock_exams")
        .select("user_id, score, accuracy, duration, completed_at")
        .order("completed_at", desc=True)
        .limit(500)
        .execute()
    )
    return rows.data or []


def _user_label(user: dict) -> str:
    name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
    return name or user.get("email") or "Unknown"


def fetch_student_performance_summary() -> list[dict]:
    users = _fetch_users()
    attempts = _fetch_practice_attempts()
    exams = _fetch_mock_exams()

    practice_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"total": 0, "correct": 0, "last_activity": None}
    )
    for row in attempts:
        user_id = row["user_id"]
        practice_stats[user_id]["total"] += 1
        if row.get("is_correct"):
            practice_stats[user_id]["correct"] += 1
        created_at = row.get("created_at")
        if created_at and (
            practice_stats[user_id]["last_activity"] is None
            or created_at > practice_stats[user_id]["last_activity"]
        ):
            practice_stats[user_id]["last_activity"] = created_at

    exam_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "latest_score": None, "latest_completed_at": None}
    )
    for row in exams:
        user_id = row["user_id"]
        exam_stats[user_id]["count"] += 1
        completed_at = row.get("completed_at")
        if completed_at and (
            exam_stats[user_id]["latest_completed_at"] is None
            or completed_at > exam_stats[user_id]["latest_completed_at"]
        ):
            exam_stats[user_id]["latest_completed_at"] = completed_at
            exam_stats[user_id]["latest_score"] = row.get("score")

        if completed_at and (
            practice_stats[user_id]["last_activity"] is None
            or completed_at > practice_stats[user_id]["last_activity"]
        ):
            practice_stats[user_id]["last_activity"] = completed_at

    summary = []
    for user in users:
        user_id = user["user_id"]
        practice = practice_stats[user_id]
        exam = exam_stats[user_id]
        total = practice["total"]
        accuracy = round(practice["correct"] / total * 100, 1) if total else None

        if not total and not exam["count"]:
            continue

        summary.append(
            {
                "student": _user_label(user),
                "email": user.get("email"),
                "role": user.get("role"),
                "practice_attempts": total,
                "practice_accuracy_pct": accuracy,
                "mock_exams": exam["count"],
                "latest_mock_score": exam["latest_score"],
                "last_activity": practice["last_activity"],
            }
        )

    summary.sort(
        key=lambda row: row.get("last_activity") or "",
        reverse=True,
    )
    return summary


def fetch_exam_history() -> list[dict]:
    users = {u["user_id"]: u for u in _fetch_users()}
    exams = _fetch_mock_exams()

    history = []
    for row in exams:
        user = users.get(row["user_id"], {})
        history.append(
            {
                "student": _user_label(user),
                "email": user.get("email"),
                "score": row.get("score"),
                "accuracy_pct": float(row.get("accuracy") or 0),
                "duration_sec": row.get("duration"),
                "completed_at": row.get("completed_at"),
            }
        )
    return history
