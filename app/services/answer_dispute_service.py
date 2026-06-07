from __future__ import annotations

from datetime import datetime, timezone

from app.database.supabase_client import get_supabase_admin_client, get_supabase_client
from app.services.question_cache import clear_question_cache

_disputes_table_available: bool | None = None

_DISPUTE_SELECT = (
    "dispute_id,user_id,question_id,selected_answer,stored_answer,proposed_answer,"
    "reason,status,admin_notes,reviewed_by,reviewed_at,created_at,"
    "questions(question_id,exam_type,subject,topic,difficulty,question_text,passage,"
    "options,answer,explanation,strategy_tip,source),"
    "users!answer_disputes_user_id_fkey(first_name,last_name,email)"
)

_QUESTION_SELECT = (
    "question_id,exam_type,subject,topic,difficulty,question_text,passage,"
    "options,answer,explanation,strategy_tip,source"
)
_USER_SELECT = "first_name,last_name,email"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def disputes_schema_ready() -> bool:
    """True when the answer_disputes table exists."""
    global _disputes_table_available
    if _disputes_table_available is not None:
        return _disputes_table_available
    try:
        get_supabase_admin_client().table("answer_disputes").select("dispute_id").limit(1).execute()
        _disputes_table_available = True
    except Exception:
        _disputes_table_available = False
    return _disputes_table_available


def has_pending_dispute(*, user_id: str, question_id: str) -> bool:
    if not disputes_schema_ready():
        return False
    try:
        rows = (
            get_supabase_client()
            .table("answer_disputes")
            .select("dispute_id")
            .eq("user_id", user_id)
            .eq("question_id", question_id)
            .eq("status", "pending")
            .limit(1)
            .execute()
        )
        return bool(rows.data)
    except Exception:
        return False


def submit_dispute(
    *,
    user_id: str,
    question_id: str,
    selected_answer: str,
    stored_answer: str,
    proposed_answer: str,
    reason: str,
) -> dict:
    if not disputes_schema_ready():
        raise RuntimeError(
            "Answer disputes are not enabled yet. Run app/database/migrations/002_answer_disputes.sql "
            "in the Supabase SQL Editor."
        )
    proposed = proposed_answer.strip()
    comment = reason.strip()
    if not proposed:
        raise ValueError("Please choose or enter the answer you believe is correct.")
    if not comment:
        raise ValueError("Please explain why you think the stored answer is wrong.")
    if has_pending_dispute(user_id=user_id, question_id=question_id):
        raise ValueError("You already have a pending dispute for this question.")

    row = {
        "user_id": user_id,
        "question_id": question_id,
        "selected_answer": selected_answer.strip(),
        "stored_answer": stored_answer.strip(),
        "proposed_answer": proposed,
        "reason": comment,
        "status": "pending",
    }
    response = get_supabase_client().table("answer_disputes").insert(row).execute()
    if not response.data:
        raise RuntimeError("Could not save your dispute. Please try again.")
    return response.data[0]


def _execute_disputes_query(*, select: str, status: str | None, limit: int):
    query = get_supabase_admin_client().table("answer_disputes").select(select)
    if status:
        query = query.eq("status", status)
    return query.order("created_at", desc=True).limit(limit).execute()


def _attach_related_records(rows: list[dict]) -> list[dict]:
    if not rows:
        return rows

    client = get_supabase_admin_client()
    question_ids = sorted({row["question_id"] for row in rows if row.get("question_id")})
    user_ids = sorted({row["user_id"] for row in rows if row.get("user_id")})

    questions_by_id: dict[str, dict] = {}
    if question_ids:
        question_rows = (
            client.table("questions")
            .select(_QUESTION_SELECT)
            .in_("question_id", question_ids)
            .execute()
        )
        questions_by_id = {
            row["question_id"]: row for row in (question_rows.data or []) if row.get("question_id")
        }

    users_by_id: dict[str, dict] = {}
    if user_ids:
        user_rows = (
            client.table("users")
            .select(_USER_SELECT + ",user_id")
            .in_("user_id", user_ids)
            .execute()
        )
        users_by_id = {row["user_id"]: row for row in (user_rows.data or []) if row.get("user_id")}

    enriched: list[dict] = []
    for row in rows:
        merged = dict(row)
        merged.setdefault("questions", questions_by_id.get(row.get("question_id", ""), {}))
        merged.setdefault("users", users_by_id.get(row.get("user_id", ""), {}))
        enriched.append(merged)
    return enriched


def fetch_disputes(*, status: str | None = "pending", limit: int = 100) -> list[dict]:
    if not disputes_schema_ready():
        return []
    try:
        rows = _execute_disputes_query(select=_DISPUTE_SELECT, status=status, limit=limit)
        return rows.data or []
    except Exception:
        try:
            rows = _execute_disputes_query(select="*", status=status, limit=limit)
            return _attach_related_records(rows.data or [])
        except Exception:
            return []


def resolve_dispute(
    *,
    dispute_id: str,
    status: str,
    reviewer_id: str,
    admin_notes: str | None = None,
    corrected_answer: str | None = None,
    corrected_explanation: str | None = None,
) -> dict:
    if status not in {"accepted", "rejected"}:
        raise ValueError("Dispute status must be accepted or rejected.")
    if not disputes_schema_ready():
        raise RuntimeError("Answer disputes table is not available.")

    client = get_supabase_admin_client()
    dispute_rows = (
        client.table("answer_disputes")
        .select("dispute_id,question_id,status,proposed_answer")
        .eq("dispute_id", dispute_id)
        .limit(1)
        .execute()
    )
    if not dispute_rows.data:
        raise ValueError("Dispute not found.")
    dispute = dispute_rows.data[0]
    if dispute.get("status") != "pending":
        raise ValueError("This dispute has already been reviewed.")

    if status == "accepted":
        question_id = dispute["question_id"]
        updates: dict[str, str] = {}
        answer = (corrected_answer or dispute.get("proposed_answer") or "").strip()
        if answer:
            updates["answer"] = answer
        if corrected_explanation and corrected_explanation.strip():
            updates["explanation"] = corrected_explanation.strip()
        if updates:
            client.table("questions").update(updates).eq("question_id", question_id).execute()
            clear_question_cache()

    response = (
        client.table("answer_disputes")
        .update(
            {
                "status": status,
                "admin_notes": (admin_notes or "").strip() or None,
                "reviewed_by": reviewer_id,
                "reviewed_at": _utc_now_iso(),
            }
        )
        .eq("dispute_id", dispute_id)
        .execute()
    )
    if not response.data:
        raise RuntimeError("Could not update the dispute.")
    return response.data[0]
