"""Admin review queue for student-reported answer disputes."""

from __future__ import annotations

import json

import streamlit as st

from app.authentication.auth_service import AuthService
from app.components.answer_selector import render_answer_review
from app.services.answer_dispute_service import disputes_schema_ready, fetch_disputes, resolve_dispute
from app.utils.datetime_display import format_cst


def _format_options(options) -> list[str]:
    if isinstance(options, list):
        return [str(option) for option in options]
    if isinstance(options, str):
        text = options.strip()
        if text.startswith("[") and text.endswith("]"):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    return [str(option) for option in parsed]
            except json.JSONDecodeError:
                pass
        for separator in ("||", "|", ";", "\n"):
            if separator in text:
                return [part.strip() for part in text.split(separator) if part.strip()]
    return []


def _student_name(dispute: dict) -> str:
    user = dispute.get("users") or {}
    first = (user.get("first_name") or "").strip()
    last = (user.get("last_name") or "").strip()
    full_name = f"{first} {last}".strip()
    return full_name or (user.get("email") or "Unknown student")


def _render_dispute_card(dispute: dict, *, reviewer_id: str) -> None:
    dispute_id = dispute["dispute_id"]
    question = dispute.get("questions") or {}
    options = _format_options(question.get("options"))

    st.markdown("---")
    st.subheader(f"Dispute · {question.get('subject', '—')} · {question.get('topic', '—')}")
    st.caption(
        f"Reported by **{_student_name(dispute)}** · "
        f"{format_cst(dispute.get('created_at'))} · "
        f"Batch: {question.get('source') or '—'}"
    )

    st.markdown('<div class="card question-card">', unsafe_allow_html=True)
    st.markdown(f"### {question.get('question_text', 'Question')}")
    if question.get("passage"):
        with st.expander("Passage"):
            st.write(question["passage"])
    render_answer_review(
        options,
        selected=dispute.get("selected_answer"),
        correct=str(question.get("answer", "")),
    )
    st.markdown("</div>", unsafe_allow_html=True)

    detail_col1, detail_col2 = st.columns(2)
    with detail_col1:
        st.write(f"**Stored answer:** {dispute.get('stored_answer', '—')}")
        st.write(f"**Student proposes:** {dispute.get('proposed_answer', '—')}")
    with detail_col2:
        st.write(f"**Student selected:** {dispute.get('selected_answer', '—')}")
        st.write(f"**Exam / difficulty:** {question.get('exam_type', '—')} · {question.get('difficulty', '—')}")

    st.write(f"**Student reason:** {dispute.get('reason', '—')}")
    if question.get("explanation"):
        st.write(f"**Current explanation:** {question['explanation']}")

    with st.form(f"resolve_dispute_{dispute_id}"):
        corrected_answer = st.text_input(
            "Correct answer if approving",
            value=dispute.get("proposed_answer") or question.get("answer") or "",
        )
        corrected_explanation = st.text_area(
            "Updated explanation (optional)",
            value=question.get("explanation") or "",
            height=100,
        )
        admin_notes = st.text_area(
            "Admin notes (optional)",
            placeholder="Visible in the dispute record after review.",
            height=80,
        )
        accept_col, reject_col = st.columns(2)
        with accept_col:
            accept = st.form_submit_button("Approve and fix answer", type="primary")
        with reject_col:
            reject = st.form_submit_button("Reject dispute", type="secondary")

    if accept:
        try:
            resolve_dispute(
                dispute_id=dispute_id,
                status="accepted",
                reviewer_id=reviewer_id,
                admin_notes=admin_notes,
                corrected_answer=corrected_answer,
                corrected_explanation=corrected_explanation,
            )
            st.success("Dispute approved and question answer updated.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    elif reject:
        try:
            resolve_dispute(
                dispute_id=dispute_id,
                status="rejected",
                reviewer_id=reviewer_id,
                admin_notes=admin_notes,
            )
            st.success("Dispute rejected.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def render() -> None:
    st.title("Answer Disputes")
    auth = AuthService()
    auth.require_role({"admin"})

    current_user = auth.current_user()
    reviewer_id = current_user.id if current_user else ""

    if not disputes_schema_ready():
        st.warning(
            "The `answer_disputes` table is not set up yet. Run "
            "`app/database/migrations/002_answer_disputes.sql` in the Supabase SQL Editor, "
            "or re-run `app/database/schema.sql`."
        )
        return

    st.caption(
        "Students can dispute third-party question answers from the Practice page. "
        "Approve to update the stored correct answer, or reject if the original answer stands."
    )

    status_filter = st.selectbox(
        "Show disputes",
        ["pending", "accepted", "rejected", "all"],
        format_func=lambda value: {
            "pending": "Pending review",
            "accepted": "Approved",
            "rejected": "Rejected",
            "all": "All statuses",
        }[value],
    )
    disputes = fetch_disputes(status=None if status_filter == "all" else status_filter, limit=200)

    if not disputes:
        st.info("No disputes in this view.")
        return

    st.caption(f"**{len(disputes)}** dispute(s) shown.")
    if status_filter == "pending":
        for dispute in disputes:
            _render_dispute_card(dispute, reviewer_id=reviewer_id)
    else:
        rows = []
        for dispute in disputes:
            question = dispute.get("questions") or {}
            rows.append(
                {
                    "Reported": format_cst(dispute.get("created_at")),
                    "Student": _student_name(dispute),
                    "Subject": question.get("subject", "—"),
                    "Topic": question.get("topic", "—"),
                    "Stored": dispute.get("stored_answer", "—"),
                    "Proposed": dispute.get("proposed_answer", "—"),
                    "Status": dispute.get("status", "—"),
                    "Admin notes": dispute.get("admin_notes") or "—",
                }
            )
        st.dataframe(rows, width="stretch", hide_index=True)
