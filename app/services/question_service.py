from __future__ import annotations

from app.database.supabase_client import get_supabase_client

DEFAULT_QUERY_LIMIT = 10_000


class QuestionService:
    def __init__(self):
        self.client = get_supabase_client()

    def topics_for_subject(self, subject: str) -> list[str]:
        result = self.client.table("questions").select("topic").eq("subject", subject).execute()
        return sorted({row["topic"] for row in (result.data or []) if row.get("topic")})

    def get_questions(
        self,
        exam_type: str,
        subject: str,
        difficulty: str | None = None,
        topic: str | None = None,
        limit: int = DEFAULT_QUERY_LIMIT,
    ):
        query = self.client.table("questions").select("*").eq("exam_type", exam_type).eq(
            "subject", subject
        )
        if difficulty:
            query = query.eq("difficulty", difficulty)
        if topic:
            query = query.eq("topic", topic)
        return query.limit(limit).execute().data or []

    def count_questions(
        self,
        exam_type: str,
        subject: str,
        difficulty: str | None = None,
        topic: str | None = None,
    ) -> int:
        query = (
            self.client.table("questions")
            .select("question_id", count="exact")
            .eq("exam_type", exam_type)
            .eq("subject", subject)
        )
        if difficulty:
            query = query.eq("difficulty", difficulty)
        if topic:
            query = query.eq("topic", topic)
        result = query.execute()
        return result.count or 0

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
