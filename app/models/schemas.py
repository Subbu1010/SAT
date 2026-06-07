from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["admin", "teacher", "student"]
ExamType = Literal["SAT", "PSAT", "PSAT 8/9"]
Subject = Literal["Math", "Reading", "Writing"]
Difficulty = Literal["Easy", "Medium", "Hard"]


class User(BaseModel):
    user_id: str
    first_name: str
    last_name: str
    email: str
    role: Role
    created_at: datetime
    last_login: datetime | None = None


class Question(BaseModel):
    question_id: str
    exam_type: ExamType
    subject: Subject
    topic: str
    difficulty: Difficulty
    question_text: str
    options: list[str]
    answer: str
    explanation: str
    strategy_tip: str
    estimated_time: int = Field(description="Seconds")


class PracticeAttempt(BaseModel):
    attempt_id: str
    user_id: str
    question_id: str
    selected_answer: str
    is_correct: bool
    time_spent: int
    created_at: datetime


DisputeStatus = Literal["pending", "accepted", "rejected"]


class AnswerDispute(BaseModel):
    dispute_id: str
    user_id: str
    question_id: str
    selected_answer: str
    stored_answer: str
    proposed_answer: str
    reason: str
    status: DisputeStatus = "pending"
    admin_notes: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class LoginHistory(BaseModel):
    """Row shape for public.login_history (see app/database/schema.sql)."""

    id: str
    user_id: str | None = None
    email: str | None = None
    ip_address: str | None = None
    location: str | None = None
    status: str
    created_at: datetime
