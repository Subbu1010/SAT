from __future__ import annotations

from app.database.supabase_client import get_supabase_client
from app.services.question_cache import (
    MOCK_EXAM_POOL_LIMIT,
    PRACTICE_POOL_LIMIT,
    _cached_count_questions,
    _cached_get_questions,
    _cached_student_batch_context,
    _cached_topics_for_subject,
    clear_question_cache,
)

DEFAULT_QUERY_LIMIT = PRACTICE_POOL_LIMIT

__all__ = [
    "DEFAULT_QUERY_LIMIT",
    "MOCK_EXAM_POOL_LIMIT",
    "PRACTICE_POOL_LIMIT",
    "QuestionService",
    "clear_question_cache",
]


class QuestionService:
    def __init__(self):
        self.client = get_supabase_client()

    def topics_for_subject(self, subject: str) -> list[str]:
        return list(_cached_topics_for_subject(subject))

    def _student_batch_context(self) -> dict[str, str | None]:
        return _cached_student_batch_context()

    def get_latest_import_source(self) -> str | None:
        """Return the raw source key for the active student question batch, if any."""
        return self._student_batch_context().get("raw_source")

    def get_active_student_batch_label(self) -> str:
        """Human-readable batch name shown to students during practice and mock exams."""
        return self._student_batch_context().get("display_label") or "OpenSAT-01/01/2026"

    def get_questions(
        self,
        exam_type: str,
        subject: str,
        difficulty: str | None = None,
        topic: str | None = None,
        source: str | None = None,
        limit: int = DEFAULT_QUERY_LIMIT,
    ):
        return list(
            _cached_get_questions(exam_type, subject, difficulty, topic, source, limit)
        )

    def get_questions_for_students(
        self,
        exam_type: str,
        subject: str,
        difficulty: str | None = None,
        topic: str | None = None,
        limit: int = DEFAULT_QUERY_LIMIT,
    ):
        """Prefer the latest admin import batch; otherwise use the full question bank."""
        latest_source = self.get_latest_import_source()
        if latest_source:
            pool = self.get_questions(
                exam_type=exam_type,
                subject=subject,
                difficulty=difficulty,
                topic=topic,
                source=latest_source,
                limit=limit,
            )
            if pool:
                return pool
        return self.get_questions(
            exam_type=exam_type,
            subject=subject,
            difficulty=difficulty,
            topic=topic,
            limit=limit,
        )

    def count_questions(
        self,
        exam_type: str,
        subject: str,
        difficulty: str | None = None,
        topic: str | None = None,
        source: str | None = None,
    ) -> int:
        return _cached_count_questions(exam_type, subject, difficulty, topic, source)

    def count_questions_for_students(
        self,
        exam_type: str,
        subject: str,
        difficulty: str | None = None,
        topic: str | None = None,
    ) -> int:
        latest_source = self.get_latest_import_source()
        if latest_source:
            count = self.count_questions(
                exam_type=exam_type,
                subject=subject,
                difficulty=difficulty,
                topic=topic,
                source=latest_source,
            )
            if count:
                return count
        return self.count_questions(
            exam_type=exam_type,
            subject=subject,
            difficulty=difficulty,
            topic=topic,
        )

    def save_attempt(
        self,
        user_id: str,
        question_id: str,
        selected_answer: str,
        is_correct: bool,
        time_spent: int,
    ):
        payload = {
            "user_id": user_id,
            "question_id": question_id,
            "selected_answer": selected_answer,
            "is_correct": is_correct,
            "time_spent": time_spent,
        }
        return self.client.table("practice_attempts").insert(payload).execute()
