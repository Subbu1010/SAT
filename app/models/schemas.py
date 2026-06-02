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
