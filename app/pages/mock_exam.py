import time

import pandas as pd
import streamlit as st

from app.authentication.auth_service import AuthService
from app.components.answer_selector import (
    answer_from_widget,
    render_answer_selector,
    restore_answer_widget,
)
from app.services.mock_exam_service import (
    DEFAULT_QUESTIONS_PER_SUBJECT,
    build_mock_exam,
    elapsed_seconds,
    save_mock_exam,
    score_exam,
)
from app.utils.compact_layout import inject_compact_spacing
from app.utils.question_shuffle import shuffled_options
from app.utils.scoped_session import scoped_has, scoped_key, uss

DEFAULT_DURATION = 60 * 60


def _init_state() -> None:
    defaults = {
        "exam_running": False,
        "exam_finished": False,
        "exam_start_ts": None,
        "exam_end_ts": None,
        "exam_duration": DEFAULT_DURATION,
        "exam_duration_total": DEFAULT_DURATION,
        "exam_remaining_secs": DEFAULT_DURATION,
        "exam_type": "SAT",
        "exam_questions": [],
        "exam_index": 0,
        "exam_answers": {},
        "exam_flagged": [],
        "exam_results": None,
    }
    for key, value in defaults.items():
        if key not in uss:
            uss[key] = value


def _exam_in_progress() -> bool:
    return bool(uss.get("exam_questions")) and not uss.get("exam_finished")


def _remaining_seconds() -> int:
    if uss.get("exam_running") and uss.get("exam_end_ts"):
        return max(0, int(uss["exam_end_ts"] - time.time()))
    return int(uss.get("exam_remaining_secs") or uss.get("exam_duration") or 0)


def _format_time(seconds: int) -> str:
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _maybe_finish_expired_exam() -> bool:
    """Auto-submit when the timer hits zero (including after navigating away)."""
    if not _exam_in_progress() or not uss.get("exam_running") or not uss.get("exam_end_ts"):
        return False
    if time.time() >= uss["exam_end_ts"]:
        _finish_exam()
        return True
    return False


def _start_exam(exam_type: str, duration_secs: int) -> bool:
    questions = build_mock_exam(exam_type)
    if not questions:
        return False

    uss["exam_type"] = exam_type
    uss["exam_questions"] = questions
    uss["exam_index"] = 0
    uss["exam_answers"] = {}
    uss["exam_flagged"] = []
    uss["exam_results"] = None
    uss["exam_finished"] = False
    uss["exam_duration_total"] = duration_secs
    uss["exam_duration"] = duration_secs
    uss["exam_remaining_secs"] = duration_secs
    uss["exam_running"] = True
    uss["exam_start_ts"] = time.time()
    uss["exam_end_ts"] = time.time() + duration_secs
    return True


def _resume_exam() -> None:
    remaining = _remaining_seconds()
    if remaining <= 0:
        _finish_exam()
        return
    uss["exam_remaining_secs"] = remaining
    uss["exam_duration"] = remaining
    uss["exam_running"] = True
    uss["exam_end_ts"] = time.time() + remaining


def _pause_exam() -> None:
    if uss.get("exam_questions"):
        _sync_exam_answers(uss["exam_questions"])
    remaining = _remaining_seconds()
    uss["exam_remaining_secs"] = remaining
    uss["exam_duration"] = remaining
    uss["exam_running"] = False
    uss["exam_end_ts"] = None


def _restore_exam_answer_widgets(questions: list[dict]) -> None:
    """Seed radio widget keys from persisted answers (survives page navigation)."""
    answers = dict(uss.get("exam_answers") or {})
    if not answers:
        return
    for question in questions:
        qid = question["question_id"]
        saved = answers.get(qid)
        if not saved:
            continue
        options = shuffled_options(
            question,
            session_key=scoped_key(f"exam_opts_{qid}"),
        )
        if saved not in options:
            continue
        restore_answer_widget(scoped_key(f"exam_ans_{qid}"), options, saved)


def _sync_exam_answers(questions: list[dict]) -> dict[str, str]:
    """Merge saved answers with any in-progress widget selections."""
    answers = dict(uss.get("exam_answers", {}))
    for question in questions:
        qid = question["question_id"]
        widget_key = scoped_key(f"exam_ans_{qid}")
        if widget_key in st.session_state:
            opts_key = scoped_key(f"exam_opts_{qid}")
            options = list(st.session_state.get(opts_key) or [])
            picked = answer_from_widget(options, st.session_state[widget_key])
            if picked:
                answers[qid] = picked
    uss["exam_answers"] = answers
    return answers


def _finish_exam() -> None:
    questions = uss["exam_questions"]
    answers = _sync_exam_answers(questions)
    results = score_exam(
        questions,
        answers,
        exam_type=uss.get("exam_type", "SAT"),
    )
    duration = elapsed_seconds(
        uss["exam_start_ts"] or time.time(),
        time.time(),
    )

    user = AuthService().current_user()
    if user:
        try:
            save_mock_exam(user.id, results, duration)
        except Exception as exc:
            st.warning(f"Could not save exam results: {exc}")

    uss["exam_results"] = {
        **results,
        "duration": duration,
        "exam_type": uss.get("exam_type", "SAT"),
    }
    uss["exam_running"] = False
    uss["exam_finished"] = True
    uss["exam_index"] = 0


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
        key=scoped_key("exam_review_filter"),
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
    results = uss["exam_results"]
    if not results:
        st.warning("Exam ended but results are unavailable. Please start a new exam.")
        if st.button("Start new exam", key=scoped_key("recover_new_exam")):
            uss["exam_finished"] = False
            uss["exam_results"] = None
            uss["exam_questions"] = []
            uss["exam_running"] = False
            uss["exam_end_ts"] = None
            uss["exam_remaining_secs"] = DEFAULT_DURATION
            uss["exam_duration_total"] = DEFAULT_DURATION
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
    exam_type = results.get("exam_type", uss.get("exam_type", "SAT"))

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
        uss["exam_finished"] = False
        uss["exam_results"] = None
        uss["exam_questions"] = []
        uss["exam_answers"] = {}
        uss["exam_flagged"] = []
        uss["exam_running"] = False
        uss["exam_end_ts"] = None
        uss["exam_remaining_secs"] = DEFAULT_DURATION
        uss["exam_duration_total"] = DEFAULT_DURATION
        st.rerun()


def _question_index(questions: list[dict], question_id: str) -> int | None:
    for idx, question in enumerate(questions):
        if question["question_id"] == question_id:
            return idx
    return None


def _flagged_indices(questions: list[dict]) -> list[int]:
    flagged_ids = set(uss["exam_flagged"])
    return [
        idx
        for idx, question in enumerate(questions)
        if question["question_id"] in flagged_ids
    ]


def _render_flagged_panel(questions: list[dict]) -> None:
    flagged_ids = uss["exam_flagged"]
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
            answer = uss["exam_answers"].get(qid)
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
                if st.button("Go", key=scoped_key(f"goto_flag_{qid}")):
                    uss["exam_index"] = idx
                    st.rerun()
            st.divider()


def _nav_button_label(
    idx: int,
    questions: list[dict],
    flagged_ids: set[str],
    answers: dict[str, str],
) -> str:
    qid = questions[idx]["question_id"]
    number = str(idx + 1)
    if qid in flagged_ids:
        return f"{number}🚩"
    if qid in answers:
        return f"{number}✓"
    return number


def _render_question_nav(questions: list[dict], total: int) -> None:
    flagged_only = uss.get("exam_review_flagged_only", False)
    flagged_idxs = _flagged_indices(questions)
    if flagged_only:
        if not flagged_idxs:
            st.caption("Flag at least one question to use review mode.")
            return
        if uss["exam_index"] not in flagged_idxs:
            uss["exam_index"] = flagged_idxs[0]
            st.rerun()

    display_indices = flagged_idxs if flagged_only else list(range(len(questions)))
    nav_disabled = not questions or (flagged_only and not flagged_idxs)
    flagged_ids = set(uss["exam_flagged"])
    answers = uss["exam_answers"]
    current = uss["exam_index"]
    n = len(display_indices)

    st.markdown(
        """
        <style>
        .exam-nav-block + div[data-testid="stHorizontalBlock"] {
          overflow-x: auto;
          overflow-y: hidden;
          flex-wrap: nowrap !important;
          gap: 0.2rem;
          padding-bottom: 0.1rem;
        }
        .exam-nav-block + div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
          width: auto !important;
          min-width: 2.6rem;
          flex: 0 0 auto !important;
        }
        .exam-nav-block + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child,
        .exam-nav-block + div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child {
          min-width: 2.4rem;
        }
        .exam-nav-block + div[data-testid="stHorizontalBlock"] button {
          white-space: nowrap !important;
          min-width: 2.4rem;
          min-height: 1.85rem;
          padding: 0.2rem 0.4rem;
          font-size: 0.78rem;
          line-height: 1.1;
        }
        .exam-nav-block + div[data-testid="stHorizontalBlock"] button p {
          white-space: nowrap !important;
        }
        </style>
        <div class="exam-nav-block"></div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns([1] + [1] * n + [1])
    with cols[0]:
        if st.button("◀", key=scoped_key("exam_prev"), disabled=nav_disabled, use_container_width=True):
            if flagged_only and flagged_idxs:
                if current not in flagged_idxs:
                    uss["exam_index"] = flagged_idxs[-1]
                else:
                    pos = flagged_idxs.index(current)
                    if pos > 0:
                        uss["exam_index"] = flagged_idxs[pos - 1]
            elif current > 0:
                uss["exam_index"] = current - 1
            st.rerun()

    for i, idx in enumerate(display_indices):
        with cols[i + 1]:
            if st.button(
                _nav_button_label(idx, questions, flagged_ids, answers),
                key=scoped_key(f"nav_q_{idx}"),
                type="primary" if idx == current else "secondary",
                use_container_width=False,
            ):
                uss["exam_index"] = idx
                st.rerun()

    with cols[-1]:
        if st.button("▶", key=scoped_key("exam_next"), disabled=nav_disabled, use_container_width=True):
            if flagged_only and flagged_idxs:
                if current not in flagged_idxs:
                    uss["exam_index"] = flagged_idxs[0]
                else:
                    pos = flagged_idxs.index(current)
                    if pos < len(flagged_idxs) - 1:
                        uss["exam_index"] = flagged_idxs[pos + 1]
            elif current < total - 1:
                uss["exam_index"] = current + 1
            st.rerun()


@st.fragment(run_every=1)
def _exam_timer_tick() -> None:
    """Refresh the countdown every second while the exam is running."""
    if not uss.get("exam_running") or not _exam_in_progress():
        return
    if _maybe_finish_expired_exam():
        st.rerun(scope="app")
    remaining = _remaining_seconds()
    total = uss.get("exam_duration_total") or uss.get("exam_duration") or DEFAULT_DURATION
    if total > 0:
        st.progress(
            1 - (remaining / total),
            text=f"Time remaining: {_format_time(remaining)}",
        )


def _render_active_exam() -> None:
    questions = uss["exam_questions"]
    if not questions:
        st.warning("No questions loaded for this exam.")
        return

    _restore_exam_answer_widgets(questions)
    _exam_timer_tick()

    index = uss["exam_index"]
    question = questions[index]
    qid = question["question_id"]
    total = len(questions)

    answered = len(uss["exam_answers"])
    flagged_count = len(uss["exam_flagged"])
    remaining = total - answered
    cap_col, flag_col = st.columns([5, 1])
    with cap_col:
        st.caption(
            f"Question {index + 1} of {total} — "
            f"{question.get('subject')} · {question.get('topic')} · {question.get('difficulty')} · "
            f"Answered: {answered} · Remaining: {remaining} · Flagged: {flagged_count}"
        )
    with flag_col:
        st.checkbox(
            "Flagged only",
            key=scoped_key("exam_review_flagged_only"),
            help="Navigator shows flagged questions only; Previous/Next move between them.",
        )
    _render_question_nav(questions, total)
    if uss.get("exam_review_flagged_only"):
        _render_flagged_panel(questions)

    st.markdown('<div class="card question-card">', unsafe_allow_html=True)
    st.markdown(f"### {question.get('question_text', 'Question')}")
    if question.get("passage"):
        with st.expander("Passage"):
            st.write(question["passage"])

    options = shuffled_options(question, session_key=scoped_key(f"exam_opts_{qid}"))
    if options:
        widget_key = scoped_key(f"exam_ans_{qid}")
        saved = (uss.get("exam_answers") or {}).get(qid)
        selected = render_answer_selector(
            options,
            widget_key=widget_key,
            saved=saved,
        )
        if selected:
            answers = dict(uss.get("exam_answers") or {})
            answers[qid] = selected
            uss["exam_answers"] = answers

    _sync_exam_answers(questions)

    flag_col, _ = st.columns([1, 3])
    flagged = qid in uss["exam_flagged"]
    if flag_col.button("Unflag" if flagged else "Flag", key=scoped_key(f"exam_flag_{qid}")):
        if flagged:
            uss["exam_flagged"].remove(qid)
        else:
            uss["exam_flagged"].append(qid)
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render():
    inject_compact_spacing()
    st.title("Timed Mock Exam")
    _init_state()

    if uss["exam_finished"] and uss["exam_results"]:
        _render_results()
        return

    if _maybe_finish_expired_exam():
        st.rerun()
        return

    in_progress = _exam_in_progress()
    running = bool(uss.get("exam_running"))

    if in_progress:
        questions = uss.get("exam_questions") or []
        if questions:
            _restore_exam_answer_widgets(questions)
            _sync_exam_answers(questions)

    if not in_progress:
        setup_col1, setup_col2 = st.columns(2)
        with setup_col1:
            uss["exam_type"] = st.selectbox(
                "Exam Type",
                ["SAT", "PSAT", "PSAT 8/9"],
                index=["SAT", "PSAT", "PSAT 8/9"].index(uss["exam_type"]),
            )
        with setup_col2:
            duration_mins = st.selectbox("Duration (min)", [30, 45, 60], index=2)
        setup_duration_secs = duration_mins * 60
        st.caption(
            f"Up to {DEFAULT_QUESTIONS_PER_SUBJECT} questions per subject "
            f"({DEFAULT_QUESTIONS_PER_SUBJECT * 3} total, shuffled)"
        )
    else:
        answered = len(uss.get("exam_answers", {}))
        total_q = len(uss.get("exam_questions", []))
        progress_bits = [
            f"{uss.get('exam_type', 'SAT')} mock exam in progress",
            f"{answered}/{total_q} answered",
        ]
        if not running:
            progress_bits.append(f"time remaining {_format_time(_remaining_seconds())}")
        st.caption(" — ".join(progress_bits))
        if not running:
            st.info(
                f"Exam paused. Time remaining: **{_format_time(_remaining_seconds())}**. "
                "Click **Resume Test** to continue. You can leave this page and return later — "
                "your progress and remaining time are saved."
            )

    c1, c2, c3 = st.columns(3)
    if running:
        c1.button("Start Test", type="primary", disabled=True)
        if c2.button("Pause"):
            _pause_exam()
            st.rerun()
    elif in_progress:
        if c1.button("Resume Test", type="primary"):
            _resume_exam()
            st.rerun()
        c2.button("Pause", disabled=True)
    else:
        if c1.button("Start Test", type="primary"):
            if _start_exam(uss["exam_type"], setup_duration_secs):
                st.rerun()
            else:
                st.error(
                    "No questions found for this exam type. "
                    "Run `python scripts/seed_bulk_questions.py` or use Admin → Seed practice bank."
                )
        c2.button("Pause", disabled=True)

    if c3.button("End Test", disabled=not in_progress):
        _finish_exam()
        st.rerun()

    if in_progress and running:
        _render_active_exam()
