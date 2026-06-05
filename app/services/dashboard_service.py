from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from app.database.supabase_client import get_supabase_client


def _parse_date(value: str | datetime | None) -> date | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _count_practice_attempts(user_id: str) -> int:
    result = (
        get_supabase_client()
        .table("practice_attempts")
        .select("attempt_id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    return result.count or 0


def _fetch_practice_attempts(user_id: str) -> list[dict]:
    result = (
        get_supabase_client()
        .table("practice_attempts")
        .select("is_correct, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(5000)
        .execute()
    )
    return result.data or []


def _fetch_mock_exams(user_id: str) -> list[dict]:
    result = (
        get_supabase_client()
        .table("mock_exams")
        .select("score, accuracy, completed_at, subject_breakdown")
        .eq("user_id", user_id)
        .order("completed_at", desc=True)
        .execute()
    )
    return result.data or []


def _mock_questions_from_exam(exam: dict) -> int:
    breakdown = exam.get("subject_breakdown") or {}
    summary = breakdown.get("__summary__")
    if summary:
        return int(summary.get("questions_answered") or 0)

    # Legacy exams: use total questions across subjects in the completed exam.
    return sum(
        int(stats.get("total", 0))
        for key, stats in breakdown.items()
        if key != "__summary__" and isinstance(stats, dict)
    )


def _mock_questions_in_range(exams: list[dict], start: date, end: date) -> int:
    total = 0
    for exam in exams:
        exam_date = _parse_date(exam.get("completed_at"))
        if exam_date and start <= exam_date <= end:
            total += _mock_questions_from_exam(exam)
    return total


def _count_in_range(rows: list[dict], date_field: str, start: date, end: date) -> int:
    count = 0
    for row in rows:
        row_date = _parse_date(row.get(date_field))
        if row_date and start <= row_date <= end:
            count += 1
    return count


def _accuracy_in_range(attempts: list[dict], start: date, end: date) -> float | None:
    filtered = []
    for row in attempts:
        row_date = _parse_date(row.get("created_at"))
        if row_date and start <= row_date <= end:
            filtered.append(row)
    if not filtered:
        return None
    correct = sum(1 for row in filtered if row.get("is_correct"))
    return round(correct / len(filtered) * 100, 1)


def _compute_streak(activity_dates: set[date]) -> int:
    if not activity_dates:
        return 0

    today = date.today()
    if today not in activity_dates and today - timedelta(days=1) not in activity_dates:
        return 0

    streak = 0
    current = today if today in activity_dates else today - timedelta(days=1)
    while current in activity_dates:
        streak += 1
        current -= timedelta(days=1)
    return streak


def get_dashboard_stats(user_id: str) -> dict[str, Any]:
    attempts = _fetch_practice_attempts(user_id)
    exams = _fetch_mock_exams(user_id)

    practice_attempted = _count_practice_attempts(user_id)
    mock_questions = sum(_mock_questions_from_exam(exam) for exam in exams)
    total_attempted = practice_attempted + mock_questions

    today = date.today()
    week_start = today - timedelta(days=6)
    prev_week_start = today - timedelta(days=13)
    prev_week_end = today - timedelta(days=7)

    this_week_practice = _count_in_range(attempts, "created_at", week_start, today)
    last_week_practice = _count_in_range(attempts, "created_at", prev_week_start, prev_week_end)
    this_week_mock = _mock_questions_in_range(exams, week_start, today)
    last_week_mock = _mock_questions_in_range(exams, prev_week_start, prev_week_end)
    attempts_delta = (this_week_practice + this_week_mock) - (last_week_practice + last_week_mock)

    correct = sum(1 for row in attempts if row.get("is_correct"))
    accuracy = round(correct / practice_attempted * 100, 1) if practice_attempted else 0.0

    this_week_accuracy = _accuracy_in_range(attempts, week_start, today)
    last_week_accuracy = _accuracy_in_range(attempts, prev_week_start, prev_week_end)
    accuracy_delta = None
    if this_week_accuracy is not None and last_week_accuracy is not None:
        accuracy_delta = round(this_week_accuracy - last_week_accuracy, 1)

    exam_scores = [row["score"] for row in exams if row.get("score") is not None]
    avg_score = round(sum(exam_scores) / len(exam_scores)) if exam_scores else None
    score_delta = None
    if len(exam_scores) >= 2:
        score_delta = exam_scores[0] - exam_scores[1]

    activity_dates: set[date] = set()
    for row in attempts:
        row_date = _parse_date(row.get("created_at"))
        if row_date:
            activity_dates.add(row_date)
    for row in exams:
        row_date = _parse_date(row.get("completed_at"))
        if row_date:
            activity_dates.add(row_date)

    streak = _compute_streak(activity_dates)

    weekly_rows = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        practice_count = _count_in_range(attempts, "created_at", day, day)
        mock_count = _mock_questions_in_range(exams, day, day)
        weekly_rows.append(
            {
                "day": day.strftime("%a"),
                "questions": practice_count + mock_count,
                "practice": practice_count,
                "mock": mock_count,
            }
        )

    monthly_rows = []
    for week_index in range(3, -1, -1):
        week_end = today - timedelta(days=week_index * 7)
        week_start_row = week_end - timedelta(days=6)
        week_exams = [
            row["score"]
            for row in exams
            if (d := _parse_date(row.get("completed_at"))) and week_start_row <= d <= week_end
        ]
        week_accuracy = _accuracy_in_range(attempts, week_start_row, week_end)
        if week_exams:
            value = round(sum(week_exams) / len(week_exams))
            metric = "score"
        elif week_accuracy is not None:
            value = week_accuracy
            metric = "accuracy"
        else:
            value = None
            metric = "score"
        monthly_rows.append(
            {
                "week": f"W{4 - week_index}",
                "score": value,
                "metric": metric,
            }
        )

    return {
        "total_attempted": total_attempted,
        "practice_attempted": practice_attempted,
        "mock_questions": mock_questions,
        "attempts_delta": attempts_delta,
        "accuracy": accuracy,
        "accuracy_delta": accuracy_delta,
        "avg_score": avg_score,
        "score_delta": score_delta,
        "streak": streak,
        "weekly_activity": pd.DataFrame(weekly_rows),
        "monthly_progress": pd.DataFrame(monthly_rows),
        "has_data": bool(practice_attempted or mock_questions or exams),
    }
