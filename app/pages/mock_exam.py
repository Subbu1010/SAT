import time

import pandas as pd
import streamlit as st

from app.authentication.auth_service import AuthService
from app.services.mock_exam_service import (
    DEFAULT_QUESTIONS_PER_SUBJECT,
    build_mock_exam,
    elapsed_seconds,
    save_mock_exam,
    score_exam,
)

DEFAULT_DURATION = 60 * 60


def _init_state() -> None:
    defaults = {
        "exam_running": False,
        "exam_finished": False,
        "exam_start_ts": None,
        "exam_end_ts": None,
        "exam_duration": DEFAULT_DURATION,
        "exam_type": "SAT",
        "exam_questions": [],
        "exam_index": 0,
        "exam_answers": {},
        "exam_flagged": [],
        "exam_results": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _start_exam(exam_type: str) -> bool:
    questions = build_mock_exam(exam_type)
    if not questions:
        return False

    st.session_state["exam_type"] = exam_type
    st.session_state["exam_questions"] = questions
    st.session_state["exam_index"] = 0
    st.session_state["exam_answers"] = {}
    st.session_state["exam_flagged"] = []
    st.session_state["exam_results"] = None
    st.session_state["exam_finished"] = False
    st.session_state["exam_running"] = True
    st.session_state["exam_start_ts"] = time.time()
    st.session_state["exam_end_ts"] = time.time() + st.session_state["exam_duration"]
    return True


def _sync_exam_answers(questions: list[dict]) -> dict[str, str]:
    """Merge saved answers with any in-progress widget selections."""
    answers = dict(st.session_state.get("exam_answers", {}))
    for question in questions:
        qid = question["question_id"]
        widget_key = f"exam_ans_{qid}"
        if widget_key in st.session_state and st.session_state[widget_key]:
            answers[qid] = st.session_state[widget_key]
    st.session_state["exam_answers"] = answers
    return answers


def _finish_exam() -> None:
    questions = st.session_state["exam_questions"]
    answers = _sync_exam_answers(questions)
    results = score_exam(
        questions,
        answers,
        exam_type=st.session_state.get("exam_type", "SAT"),
    )
    duration = elapsed_seconds(
        st.session_state["exam_start_ts"] or time.time(),
        time.time(),
    )

    user = AuthService().current_user()
    if user:
        try:
            save_mock_exam(user.id, results, duration)
        except Exception as exc:
            st.warning(f"Could not save exam results: {exc}")

    st.session_state["exam_results"] = {
        **results,
        "duration": duration,
        "exam_type": st.session_state.get("exam_type", "SAT"),
    }
    st.session_state["exam_running"] = False
    st.session_state["exam_finished"] = True
    st.session_state["exam_index"] = 0


def _status_label(status: str) -> str:
    return {
        "correct": "Correct",
        "incorrect": "Incorrect",
        "unanswered": "Unanswered",
    }.get(status, status)


def _status_icon(status: str) -> str:
    return {
        "correct": "✅",
        "incorrect": "❌",
        "unanswered": "⏭️",
    }.get(status, "•")


def _render_question_review(results: dict) -> None:
    review = results.get("question_review", [])
    if not review:
        return

    st.subheader("Question Review")
    filter_choice = st.radio(
        "Filter",
        ["All", "Correct", "Incorrect", "Unanswered"],
        horizontal=True,
        key="exam_review_filter",
    )
    filter_map = {
        "Correct": "correct",
        "Incorrect": "incorrect",
        "Unanswered": "unanswered",
    }
    if filter_choice != "All":
        review = [item for item in review if item["status"] == filter_map[filter_choice]]

    if not review:
        st.caption(f"No {filter_choice.lower()} questions.")
        return

    for item in review:
        icon = _status_icon(item["status"])
        label = (
            f"{icon} Q{item['number']} — {item['subject']} · {item['topic']} · "
            f"{_status_label(item['status'])}"
        )
        points = item.get("points_earned", 0)
        possible = item.get("points_possible", 1)
        sat_earned = item.get("sat_earned", 0)
        sat_possible = item.get("sat_possible", 0)
        label = f"{label} — {sat_earned}/{sat_possible} SAT pts"
        with st.expander(label, expanded=item["status"] != "correct"):
            st.markdown(f"**{item['question_text']}**")
            st.write(f"**Points:** {points} / {possible}")
            st.write(f"**SAT score contribution:** {sat_earned} / {sat_possible} pts")
            if item["selected"]:
                st.write(f"**Your answer:** {item['selected']}")
            else:
                st.write("**Your answer:** Not answered")
            st.write(f"**Correct answer:** {item['correct_answer']}")
            if item["status"] != "correct":
                st.write(f"**Explanation:** {item['explanation']}")
                if item.get("strategy_tip"):
                    st.write(f"**Strategy tip:** {item['strategy_tip']}")


def _render_results() -> None:
    results = st.session_state["exam_results"]
    if not results:
        st.warning("Exam ended but results are unavailable. Please start a new exam.")
        if st.button("Start new exam", key="recover_new_exam"):
            st.session_state["exam_finished"] = False
            st.session_state["exam_results"] = None
            st.session_state["exam_questions"] = []
            st.rerun()
        return

    raw_score = results.get("raw_score", results.get("correct", 0))
    total_points = results.get("total_points", results.get("total", 0))
    accuracy = results.get("accuracy", 0)
    sat_earned = results.get("sat_earned_total", results.get("score", 0))
    sat_possible = results.get("sat_possible_total", 0)
    composite_score = results.get("composite_score", results.get("score_min", 400) + sat_earned)
    score_min = results.get("score_min", 400)
    score_max = results.get("score_max", 1600)
    sat_per_q = results.get("sat_per_question_max", 0)
    exam_type = results.get("exam_type", st.session_state.get("exam_type", "SAT"))

    st.success("Exam complete!")
    st.markdown(
        f"### Final score: **{raw_score} / {total_points}** "
        f"({accuracy}% correct)"
    )
    st.markdown(
        f"### Estimated {exam_type} score: **{sat_earned} / {sat_possible}**"
    )
    st.caption(
        f"{sat_per_q} SAT pts per correct question. "
        f"Composite score on full {score_min}–{score_max} scale: **{composite_score}**."
    )

    mins, secs = divmod(results["duration"], 60)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Questions correct", f"{raw_score}/{total_points}")
    c2.metric("Accuracy", f"{accuracy}%")
    c3.metric("SAT score", f"{sat_earned}/{sat_possible}")
    c4.metric("Time taken", f"{mins}m {secs}s")

    summary_cols = st.columns(3)
    summary_cols[0].metric("Correct", results.get("correct", 0))
    summary_cols[1].metric("Incorrect", results.get("incorrect", 0))
    summary_cols[2].metric("Unanswered", results.get("unanswered", 0))

    with st.expander("Subject breakdown", expanded=True):
        for subject, stats in results["subject_breakdown"].items():
            if subject == "__summary__" or not isinstance(stats, dict):
                continue
            pct = round(stats["correct"] / stats["total"] * 100, 1) if stats["total"] else 0
            sat_earned = stats.get("sat_earned", 0)
            sat_possible = stats.get("sat_possible", 0)
            st.write(
                f"- **{subject}:** {stats['correct']}/{stats['total']} correct ({pct}%) "
                f"— **{stats['correct']}/{stats['total']} pts** "
                f"— **{sat_earned}/{sat_possible} SAT pts**"
            )

    review = results.get("question_review", [])
    if review:
        st.subheader("Score by question")
        table = pd.DataFrame(
            [
                {
                    "Question": item["number"],
                    "Subject": item["subject"],
                    "Topic": item["topic"],
                    "Your answer": item["selected"] or "—",
                    "Correct answer": item["correct_answer"],
                    "Points": f"{item.get('points_earned', 0)}/{item.get('points_possible', 1)}",
                    "SAT score": (
                        f"{item.get('sat_earned', 0)}/{item.get('sat_possible', 0)}"
                    ),
                    "Result": _status_label(item["status"]),
                }
                for item in review
            ]
        )
        st.dataframe(table, use_container_width=True, hide_index=True)

    _render_question_review(results)

    if st.button("Start new exam"):
        st.session_state["exam_finished"] = False
        st.session_state["exam_results"] = None
        st.session_state["exam_questions"] = []
        st.session_state["exam_answers"] = {}
        st.session_state["exam_flagged"] = []
        st.rerun()


def _question_index(questions: list[dict], question_id: str) -> int | None:
    for idx, question in enumerate(questions):
        if question["question_id"] == question_id:
            return idx
    return None


def _flagged_indices(questions: list[dict]) -> list[int]:
    flagged_ids = set(st.session_state["exam_flagged"])
    return [
        idx
        for idx, question in enumerate(questions)
        if question["question_id"] in flagged_ids
    ]


def _render_flagged_panel(questions: list[dict]) -> None:
    flagged_ids = st.session_state["exam_flagged"]
    if not flagged_ids:
        st.info("No flagged questions yet. Flag a question, then use **Review flagged only** to review them.")
        return

    st.subheader(f"Flagged questions ({len(flagged_ids)})")
    with st.container():
        for qid in flagged_ids:
            idx = _question_index(questions, qid)
            if idx is None:
                continue
            question = questions[idx]
            answer = st.session_state["exam_answers"].get(qid)
            status = f"Answered: {answer}" if answer else "Unanswered"
            preview = question.get("question_text", "")
            if len(preview) > 100:
                preview = preview[:100] + "..."

            col_text, col_go = st.columns([5, 1])
            with col_text:
                st.markdown(
                    f"**Q{idx + 1}** — {question.get('subject')} · {question.get('topic')} · "
                    f"{question.get('difficulty')}  \n"
                    f"{preview}  \n"
                    f"*{status}*"
                )
            with col_go:
                if st.button("Go", key=f"goto_flag_{qid}"):
                    st.session_state["exam_index"] = idx
                    st.rerun()
            st.divider()


def _render_question_grid(questions: list[dict], indices: list[int] | None = None) -> None:
    flagged_ids = set(st.session_state["exam_flagged"])
    answers = st.session_state["exam_answers"]
    current = st.session_state["exam_index"]
    cols_per_row = 10
    display_indices = indices if indices is not None else list(range(len(questions)))

    st.markdown("**Question navigator**")
    for row_start in range(0, len(display_indices), cols_per_row):
        cols = st.columns(cols_per_row)
        for col_offset, col in enumerate(cols):
            pos = row_start + col_offset
            if pos >= len(display_indices):
                break
            idx = display_indices[pos]
            question = questions[idx]
            qid = question["question_id"]
            if idx == current:
                label = f"▶ {idx + 1}"
            elif qid in flagged_ids:
                label = f"🚩 {idx + 1}"
            elif qid in answers:
                label = f"✓ {idx + 1}"
            else:
                label = str(idx + 1)

            with col:
                if st.button(label, key=f"nav_q_{idx}", use_container_width=True):
                    st.session_state["exam_index"] = idx
                    st.rerun()


def _render_question_nav(questions: list[dict], total: int) -> None:
    answered = len(st.session_state["exam_answers"])
    flagged = len(st.session_state["exam_flagged"])
    remaining = total - answered
    flagged_only = st.session_state.get("exam_review_flagged_only", False)

    st.caption(
        f"Answered: {answered} | Remaining: {remaining} | Flagged: {flagged}"
    )
    st.checkbox(
        "Review flagged only",
        key="exam_review_flagged_only",
        help="Shows flagged questions and moves Previous/Next only between them.",
    )

    flagged_idxs = _flagged_indices(questions)
    if flagged_only:
        if not flagged_idxs:
            st.caption("Flag at least one question to use review mode.")
        elif st.session_state["exam_index"] not in flagged_idxs:
            st.session_state["exam_index"] = flagged_idxs[0]
            st.rerun()

    cols = st.columns([1, 2, 1])
    nav_disabled = not questions or (flagged_only and not flagged_idxs)
    with cols[0]:
        if st.button("Previous", disabled=nav_disabled):
            if flagged_only and flagged_idxs:
                current = st.session_state["exam_index"]
                if current not in flagged_idxs:
                    st.session_state["exam_index"] = flagged_idxs[-1]
                else:
                    pos = flagged_idxs.index(current)
                    if pos > 0:
                        st.session_state["exam_index"] = flagged_idxs[pos - 1]
            elif st.session_state["exam_index"] > 0:
                st.session_state["exam_index"] -= 1
            st.rerun()
    with cols[1]:
        if flagged_only and flagged_idxs:
            jump_options = [idx + 1 for idx in flagged_idxs]
            current_pos = (
                flagged_idxs.index(st.session_state["exam_index"])
                if st.session_state["exam_index"] in flagged_idxs
                else 0
            )
            jump = st.selectbox(
                "Jump to flagged question",
                jump_options,
                index=current_pos,
                format_func=lambda n: f"Question {n} 🚩",
                label_visibility="collapsed",
            )
            new_index = jump - 1
        else:
            jump = st.selectbox(
                "Jump to question",
                list(range(1, total + 1)),
                index=st.session_state["exam_index"],
                format_func=lambda n: (
                    f"Question {n} 🚩"
                    if questions[n - 1]["question_id"] in st.session_state["exam_flagged"]
                    else f"Question {n}"
                ),
                label_visibility="collapsed",
            )
            new_index = jump - 1
        if new_index != st.session_state["exam_index"]:
            st.session_state["exam_index"] = new_index
            st.rerun()
    with cols[2]:
        if st.button("Next", disabled=nav_disabled):
            if flagged_only and flagged_idxs:
                current = st.session_state["exam_index"]
                if current not in flagged_idxs:
                    st.session_state["exam_index"] = flagged_idxs[0]
                else:
                    pos = flagged_idxs.index(current)
                    if pos < len(flagged_idxs) - 1:
                        st.session_state["exam_index"] = flagged_idxs[pos + 1]
            elif st.session_state["exam_index"] < total - 1:
                st.session_state["exam_index"] += 1
            st.rerun()

    grid_indices = flagged_idxs if flagged_only and flagged_idxs else None
    _render_question_grid(questions, grid_indices)


def _render_active_exam() -> None:
    questions = st.session_state["exam_questions"]
    if not questions:
        st.warning("No questions loaded for this exam.")
        return

    if st.session_state["exam_running"] and st.session_state["exam_end_ts"]:
        remaining = max(0, int(st.session_state["exam_end_ts"] - time.time()))
        if remaining == 0:
            _finish_exam()
            st.rerun()
            return

        progress = 1 - (remaining / st.session_state["exam_duration"])
        st.progress(
            progress,
            text=f"Time remaining: {remaining // 60:02d}:{remaining % 60:02d}",
        )

    index = st.session_state["exam_index"]
    question = questions[index]
    qid = question["question_id"]
    total = len(questions)

    st.markdown(
        f"**Question {index + 1} of {total}** — "
        f"{question.get('subject')} · {question.get('topic')} · {question.get('difficulty')}"
    )
    _render_question_nav(questions, total)
    if st.session_state.get("exam_review_flagged_only"):
        _render_flagged_panel(questions)

    st.markdown('<div class="card question-card">', unsafe_allow_html=True)
    st.markdown(f"### {question.get('question_text', 'Question')}")
    if question.get("passage"):
        with st.expander("Passage"):
            st.write(question["passage"])

    options = question.get("options", [])
    if options:
        selected = st.radio(
            "Choose your answer",
            options,
            key=f"exam_ans_{qid}",
            index=None,
        )
        if selected:
            st.session_state["exam_answers"][qid] = selected

    flag_col, _ = st.columns([1, 3])
    flagged = qid in st.session_state["exam_flagged"]
    if flag_col.button("Unflag" if flagged else "Flag", key=f"exam_flag_{qid}"):
        if flagged:
            st.session_state["exam_flagged"].remove(qid)
        else:
            st.session_state["exam_flagged"].append(qid)
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render():
    st.title("Timed Mock Exam")
    _init_state()

    if st.session_state["exam_finished"] and st.session_state["exam_results"]:
        _render_results()
        return

    if not st.session_state["exam_running"]:
        st.session_state["exam_type"] = st.selectbox(
            "Exam Type",
            ["SAT", "PSAT", "PSAT 8/9"],
            index=["SAT", "PSAT", "PSAT 8/9"].index(st.session_state["exam_type"]),
        )
        duration_mins = st.selectbox("Duration", [30, 45, 60], index=2)
        st.session_state["exam_duration"] = duration_mins * 60
        st.info(
            f"Each mock exam includes up to {DEFAULT_QUESTIONS_PER_SUBJECT} questions "
            f"per subject ({DEFAULT_QUESTIONS_PER_SUBJECT * 3} total)."
        )

    c1, c2, c3 = st.columns(3)
    if c1.button("Start Test", type="primary"):
        paused_with_questions = (
            st.session_state["exam_questions"]
            and not st.session_state["exam_running"]
            and not st.session_state["exam_finished"]
        )
        if paused_with_questions:
            st.session_state["exam_running"] = True
            st.session_state["exam_end_ts"] = time.time() + st.session_state["exam_duration"]
            st.rerun()
        elif _start_exam(st.session_state["exam_type"]):
            st.rerun()
        else:
            st.error(
                "No questions found for this exam type. "
                "Run `python scripts/seed_bulk_questions.py` or use Admin → Seed practice bank."
            )
    if c2.button("Pause", disabled=not st.session_state["exam_running"]):
        st.session_state["exam_running"] = False
        if st.session_state["exam_end_ts"]:
            st.session_state["exam_duration"] = max(
                60,
                int(st.session_state["exam_end_ts"] - time.time()),
            )
        st.session_state["exam_end_ts"] = None
        st.rerun()
    if c3.button("End Test", disabled=not st.session_state["exam_questions"]):
        _finish_exam()
        st.rerun()

    if st.session_state["exam_questions"]:
        if st.session_state["exam_running"]:
            _render_active_exam()
        else:
            st.warning("Exam paused. Click **Start Test** to resume the timer.")
            _render_active_exam()
