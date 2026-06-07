import time

import pandas as pd
import streamlit as st

from app.authentication.auth_service import AuthService
from app.components.answer_selector import (
    answer_from_widget,
    render_answer_selector,
    restore_answer_widget,
)
from app.services.adaptive_engine import next_difficulty
from app.services.mock_exam_service import (
    DEFAULT_QUESTIONS_PER_SUBJECT,
    SUBJECT_CHOICES,
    SUBJECTS,
    build_mock_exam,
    elapsed_seconds,
    sample_questions_for_subject,
    save_mock_exam,
    score_exam,
    subjects_from_choice,
)
from app.services.question_service import QuestionService
from app.services.question_source import display_batch_label
from app.utils.compact_layout import inject_compact_spacing
from app.utils.question_shuffle import shuffle_question_choices, shuffled_options
from app.utils.scoped_session import scoped_has, scoped_key, uss

DEFAULT_DURATION = 60 * 60

_EXAM_COMPACT_CSS = """
<style>
.exam-chrome { margin-bottom: 0.2rem !important; }
.exam-chrome + div[data-testid="stHorizontalBlock"] {
  margin-bottom: 0.15rem !important;
  align-items: center;
}
.exam-chrome + div[data-testid="stHorizontalBlock"] button {
  min-height: 1.65rem;
  padding: 0.15rem 0.5rem;
  font-size: 0.8rem;
}
.exam-nav-block + div[data-testid="stHorizontalBlock"] {
  overflow-x: auto;
  overflow-y: hidden;
  flex-wrap: nowrap !important;
  gap: 0.15rem;
  padding-bottom: 0;
  margin-bottom: 0;
}
.exam-nav-block + div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
  width: auto !important;
  min-width: 2.1rem;
  flex: 0 0 auto !important;
}
.exam-nav-block + div[data-testid="stHorizontalBlock"] button {
  white-space: nowrap !important;
  min-width: 2rem;
  min-height: 1.55rem;
  padding: 0.1rem 0.3rem;
  font-size: 0.72rem;
  line-height: 1;
}
div[data-testid="stExpander"]:has(.exam-nav-block) {
  margin-bottom: 0.25rem !important;
}
div[data-testid="stExpander"]:has(.exam-nav-block) details {
  border: none;
  background: transparent;
}
div[data-testid="stExpander"]:has(.exam-nav-block) summary {
  padding: 0.2rem 0 !important;
  font-size: 0.82rem;
}
.exam-timer-text {
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.2;
  margin: 0;
}
.exam-meta-line {
  font-size: 0.78rem;
  color: var(--text-color-secondary, #666);
  margin: 0 0 0.25rem 0;
  line-height: 1.3;
}
</style>
"""


def _inject_exam_compact_css() -> None:
    st.markdown(_EXAM_COMPACT_CSS, unsafe_allow_html=True)


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
        "exam_subject_choice": "All subjects",
        "exam_subjects": list(SUBJECTS),
        "exam_difficulty_mode": True,
        "exam_manual_difficulty": "Medium",
        "exam_adaptive_difficulty": "Medium",
        "exam_adaptive_results": [],
        "exam_adaptive_by_question": {},
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


def _reset_to_new_exam() -> None:
    """Clear exam state and return to the setup screen."""
    uss["exam_finished"] = False
    uss["exam_results"] = None
    uss["exam_questions"] = []
    uss["exam_answers"] = {}
    uss["exam_flagged"] = []
    uss["exam_running"] = False
    uss["exam_start_ts"] = None
    uss["exam_end_ts"] = None
    uss["exam_index"] = 0
    uss["exam_remaining_secs"] = DEFAULT_DURATION
    uss["exam_duration_total"] = DEFAULT_DURATION
    uss["exam_duration"] = DEFAULT_DURATION
    uss["exam_adaptive_difficulty"] = "Medium"
    uss["exam_adaptive_results"] = []
    uss["exam_adaptive_by_question"] = {}
    uss.pop("exam_subject_pools", None)


def _adaptive_status_message(results: list[bool]) -> str:
    if len(results) < 3:
        remaining = 3 - len(results)
        return (
            f"Adaptive: {len(results)}/3 answers — "
            f"{remaining} more before difficulty can change."
        )
    last_three = results[-3:]
    if all(last_three):
        return "Adaptive: 3 correct in a row — next questions increase in difficulty."
    if not any(last_three):
        return "Adaptive: 3 incorrect in a row — next questions decrease in difficulty."
    return "Adaptive: mixed recent results — difficulty stays the same for now."


def _refresh_remaining_questions(new_difficulty: str) -> None:
    questions = list(uss.get("exam_questions") or [])
    index = uss.get("exam_index", 0)
    pools = uss.get("exam_subject_pools") or {}
    answers = uss.get("exam_answers") or {}
    used_ids = {q["question_id"] for q in questions}

    for i in range(index + 1, len(questions)):
        q = questions[i]
        if q["question_id"] in answers:
            continue
        subject = q.get("subject", "")
        pool = pools.get(subject, [])
        replacements = sample_questions_for_subject(
            pool,
            difficulty=new_difficulty,
            count=1,
            exclude_ids=used_ids,
        )
        if not replacements:
            continue
        questions[i] = replacements[0]
        used_ids.add(replacements[0]["question_id"])

    uss["exam_questions"] = shuffle_question_choices(questions)


def _update_adaptive_for_answer(question: dict, selected: str) -> None:
    if not uss.get("exam_difficulty_mode"):
        return

    qid = question["question_id"]
    is_correct = selected == question["answer"]
    by_q = dict(uss.get("exam_adaptive_by_question") or {})
    by_q[qid] = is_correct
    uss["exam_adaptive_by_question"] = by_q

    exam_questions = uss.get("exam_questions") or []
    results = [by_q[q["question_id"]] for q in exam_questions if q["question_id"] in by_q]
    uss["exam_adaptive_results"] = results

    prev_difficulty = uss.get("exam_adaptive_difficulty", "Medium")
    new_difficulty = next_difficulty(results, prev_difficulty)
    uss["exam_adaptive_difficulty"] = new_difficulty
    if new_difficulty != prev_difficulty:
        _refresh_remaining_questions(new_difficulty)


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


def _start_exam(
    exam_type: str,
    duration_secs: int,
    subjects: list[str],
    *,
    difficulty_mode: bool,
    difficulty: str,
) -> bool:
    start_difficulty = "Medium" if difficulty_mode else difficulty
    questions, pools = build_mock_exam(
        exam_type,
        subjects=subjects,
        difficulty=start_difficulty,
        difficulty_mode=difficulty_mode,
    )
    if not questions:
        return False

    uss["exam_type"] = exam_type
    uss["exam_subjects"] = list(subjects)
    uss["exam_difficulty_mode"] = difficulty_mode
    uss["exam_manual_difficulty"] = difficulty
    uss["exam_adaptive_difficulty"] = start_difficulty
    uss["exam_adaptive_results"] = []
    uss["exam_adaptive_by_question"] = {}
    uss["exam_subject_pools"] = pools
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
                _update_adaptive_for_answer(question, picked)
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
        if st.button("Start New Exam", key=scoped_key("recover_new_exam")):
            _reset_to_new_exam()
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
        st.dataframe(table, width="stretch", hide_index=True)

    _render_question_review(results)

    if st.button("Start New Exam", key=scoped_key("results_bottom_start_new_exam")):
        _reset_to_new_exam()
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

    st.caption(f"Flagged ({len(flagged_ids)})")
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
        if st.button("◀", key=scoped_key("exam_prev"), disabled=nav_disabled, width="stretch"):
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
                width="content",
            ):
                uss["exam_index"] = idx
                st.rerun()

    with cols[-1]:
        if st.button("▶", key=scoped_key("exam_next"), disabled=nav_disabled, width="stretch"):
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
def _exam_timer_widget(*, running: bool) -> None:
    """Live countdown while the exam is running."""
    if running:
        if _maybe_finish_expired_exam():
            st.rerun(scope="app")
        icon = "⏱"
    else:
        icon = "⏸"
    st.markdown(
        f'<p class="exam-timer-text">{icon} {_format_time(_remaining_seconds())}</p>',
        unsafe_allow_html=True,
    )


def _render_exam_toolbar(*, running: bool, in_progress: bool) -> None:
    """Single compact row: timer, progress, and exam controls."""
    st.markdown('<div class="exam-chrome"></div>', unsafe_allow_html=True)
    answered = len(uss.get("exam_answers", {}))
    total_q = len(uss.get("exam_questions", []))

    t_timer, t_prog, t_pause, t_end = st.columns([1.1, 1.4, 1, 1])
    with t_timer:
        _exam_timer_widget(running=running)
    with t_prog:
        st.caption(f"{answered}/{total_q} answered")
    with t_pause:
        if running:
            if st.button("Pause", key=scoped_key("toolbar_pause")):
                _pause_exam()
                st.rerun()
        elif in_progress:
            if st.button("Resume", type="primary", key=scoped_key("toolbar_resume")):
                _resume_exam()
                st.rerun()
    with t_end:
        if st.button("End Test", key=scoped_key("toolbar_end")):
            _finish_exam()
            st.rerun()


def _render_active_exam() -> None:
    questions = uss["exam_questions"]
    if not questions:
        st.warning("No questions loaded for this exam.")
        return

    _restore_exam_answer_widgets(questions)

    index = uss["exam_index"]
    question = questions[index]
    qid = question["question_id"]
    total = len(questions)

    question_batch = display_batch_label(question.get("source"))
    flagged_count = len(uss["exam_flagged"])
    meta_bits = [
        f"Q{index + 1}/{total}",
        question_batch,
        str(question.get("subject", "")),
        str(question.get("difficulty", "")),
        f"{flagged_count} flagged",
    ]
    if uss.get("exam_difficulty_mode"):
        meta_bits.append(f"target {uss.get('exam_adaptive_difficulty', 'Medium')}")
    st.markdown(
        f'<p class="exam-meta-line">{" · ".join(meta_bits)}</p>',
        unsafe_allow_html=True,
    )
    if uss.get("exam_difficulty_mode"):
        st.caption(_adaptive_status_message(uss.get("exam_adaptive_results", [])))

    nav_col, flag_col = st.columns([4, 1])
    with nav_col:
        with st.expander(f"Jump to question ({total})", expanded=False):
            st.checkbox(
                "Flagged only",
                key=scoped_key("exam_review_flagged_only"),
                help="Show flagged questions only in the navigator.",
            )
            _render_question_nav(questions, total)
            if uss.get("exam_review_flagged_only"):
                _render_flagged_panel(questions)
    with flag_col:
        flagged = qid in uss["exam_flagged"]
        if st.button(
            "Unflag" if flagged else "Flag",
            key=scoped_key(f"exam_flag_{qid}"),
            help="Mark this question for review.",
        ):
            if flagged:
                uss["exam_flagged"].remove(qid)
            else:
                uss["exam_flagged"].append(qid)
            st.rerun()

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
            _update_adaptive_for_answer(question, selected)

    _sync_exam_answers(questions)

    st.markdown("</div>", unsafe_allow_html=True)


def render():
    inject_compact_spacing()
    _inject_exam_compact_css()
    _init_state()

    title_col, action_col = st.columns([5, 1])
    with title_col:
        st.title("Timed Mock Exam")
    with action_col:
        show_start_new = _exam_in_progress() or (
            uss.get("exam_finished") and uss.get("exam_results")
        )
        if show_start_new and st.button(
            "Start New Exam",
            key=scoped_key("page_top_start_new_exam"),
            type="secondary",
        ):
            _reset_to_new_exam()
            st.rerun()

    qs = QuestionService()
    active_batch = qs.get_active_student_batch_label()

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
        setup_col1, setup_col2, setup_col3 = st.columns(3)
        with setup_col1:
            uss["exam_type"] = st.selectbox(
                "Exam Type",
                ["SAT", "PSAT", "PSAT 8/9"],
                index=["SAT", "PSAT", "PSAT 8/9"].index(uss["exam_type"]),
            )
        with setup_col2:
            subject_choice = uss.get("exam_subject_choice", "All subjects")
            if subject_choice not in SUBJECT_CHOICES:
                subject_choice = "All subjects"
            uss["exam_subject_choice"] = st.selectbox(
                "Subjects",
                SUBJECT_CHOICES,
                index=SUBJECT_CHOICES.index(subject_choice),
                help="Choose all subjects or focus on one subject.",
            )
            uss["exam_subjects"] = subjects_from_choice(uss["exam_subject_choice"])
        with setup_col3:
            duration_mins = st.selectbox("Duration (min)", [30, 45, 60], index=2)
        setup_duration_secs = duration_mins * 60

        settings_col1, settings_col2 = st.columns(2)
        with settings_col1:
            uss["exam_difficulty_mode"] = st.toggle(
                "Adaptive mode",
                value=bool(uss.get("exam_difficulty_mode", True)),
                help="Adjust upcoming question difficulty from your recent answers.",
            )
        with settings_col2:
            if not uss["exam_difficulty_mode"]:
                manual = uss.get("exam_manual_difficulty", "Medium")
                if manual not in ("Easy", "Medium", "Hard"):
                    manual = "Medium"
                uss["exam_manual_difficulty"] = st.selectbox(
                    "Difficulty",
                    ["Easy", "Medium", "Hard"],
                    index=["Easy", "Medium", "Hard"].index(manual),
                )
            else:
                uss["exam_manual_difficulty"] = uss.get("exam_manual_difficulty", "Medium")

        subject_count = len(uss["exam_subjects"])
        total_preview = DEFAULT_QUESTIONS_PER_SUBJECT * subject_count
        difficulty_note = (
            "adaptive (starts Medium)"
            if uss["exam_difficulty_mode"]
            else uss["exam_manual_difficulty"]
        )
        st.caption(
            f"Batch: {active_batch} · {uss['exam_subject_choice']} · "
            f"up to {DEFAULT_QUESTIONS_PER_SUBJECT} per subject ({total_preview} total) · "
            f"Difficulty: {difficulty_note}"
        )
        if st.button("Start Test", type="primary", key=scoped_key("setup_start_test")):
            start_difficulty = (
                uss.get("exam_manual_difficulty", "Medium")
                if not uss["exam_difficulty_mode"]
                else "Medium"
            )
            if _start_exam(
                uss["exam_type"],
                setup_duration_secs,
                uss["exam_subjects"],
                difficulty_mode=uss["exam_difficulty_mode"],
                difficulty=start_difficulty,
            ):
                st.rerun()
            else:
                st.error(
                    "No questions found for this exam type and subject selection. "
                    "Run `python scripts/seed_bulk_questions.py` or use Admin → Seed practice bank."
                )
    else:
        if not running:
            st.caption(
                f"Paused · {_format_time(_remaining_seconds())} remaining — "
                "click **Resume** to continue."
            )
        _render_exam_toolbar(running=running, in_progress=in_progress)

    if in_progress and running:
        _render_active_exam()
