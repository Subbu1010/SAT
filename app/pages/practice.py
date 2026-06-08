import random

import streamlit as st

from app.components.answer_dispute_modal import (
    DISPUTE_OPEN_KEY,
    inject_dispute_modal_cleanup,
    open_dispute_dialog_if_needed,
    render_dispute_open_button,
    show_dispute_feedback_messages,
)
from app.components.answer_selector import render_answer_review
from app.components.question_card import render_question_card
from app.components.ti84_calculator import (
    TI84_PAGE_KEYS,
    inject_ti84_cleanup,
    render_ti84_batch_row,
)
from app.services.adaptive_engine import next_difficulty
from app.services.gemini_service import GeminiService
from app.database.exam_catalog import SUBJECT_TOPICS
from app.services.question_cache import PRACTICE_POOL_LIMIT
from app.services.question_service import QuestionService
from app.services.question_source import display_batch_label
from app.utils.compact_layout import inject_compact_spacing
from app.utils.page_session import returned_to_page
from app.utils.question_shuffle import clear_shuffled_options, shuffled_options, shuffle_questions
from app.utils.scoped_session import (
    clear_scoped_prefix,
    scoped_get,
    scoped_has,
    scoped_key,
    scoped_pop,
    scoped_set,
)


def _build_practice_queue(
    qs: QuestionService,
    *,
    exam_type: str,
    subject: str,
    topic: str | None,
    chosen_difficulty: str,
    difficulty_mode: bool,
    pool_limit: int,
) -> list[dict]:
    if difficulty_mode:
        pool = qs.get_questions_for_students(
            exam_type=exam_type,
            subject=subject,
            topic=topic,
            difficulty=chosen_difficulty,
            limit=pool_limit,
        )
        if not pool:
            pool = qs.get_questions_for_students(
                exam_type=exam_type,
                subject=subject,
                topic=topic,
                limit=pool_limit,
            )
    else:
        pool = qs.get_questions_for_students(
            exam_type=exam_type,
            subject=subject,
            topic=topic,
            difficulty=chosen_difficulty,
            limit=pool_limit,
        )
    return shuffle_questions(pool)


def _practice_queue_key(filter_key: tuple, chosen_difficulty: str, difficulty_mode: bool) -> str:
    return f"practice_queue_{filter_key}_{chosen_difficulty}_{difficulty_mode}"


def _ensure_practice_queue(
    qs: QuestionService,
    *,
    filter_key: tuple,
    exam_type: str,
    subject: str,
    topic: str | None,
    chosen_difficulty: str,
    difficulty_mode: bool,
    pool_limit: int,
) -> list[dict]:
    queue_key = _practice_queue_key(filter_key, chosen_difficulty, difficulty_mode)
    if scoped_get("practice_queue_key") != queue_key:
        scoped_set("practice_queue_key", queue_key)
        scoped_set(
            "practice_question_queue",
            _build_practice_queue(
                qs,
                exam_type=exam_type,
                subject=subject,
                topic=topic,
                chosen_difficulty=chosen_difficulty,
                difficulty_mode=difficulty_mode,
                pool_limit=pool_limit,
            ),
        )
        scoped_set("practice_queue_index", 0)
    return scoped_get("practice_question_queue", [])


def _next_practice_question(queue: list[dict]) -> dict | None:
    if not queue:
        return None
    index = scoped_get("practice_queue_index", 0)
    if index >= len(queue):
        random.shuffle(queue)
        scoped_set("practice_question_queue", queue)
        index = 0
        scoped_set("practice_queue_index", 0)
    return queue[index]


def _adaptive_status_message(results: list[bool]) -> str:
    if len(results) < 3:
        remaining = 3 - len(results)
        return (
            f"Adaptive: {len(results)}/3 answers at this topic — "
            f"{remaining} more before difficulty can change."
        )
    last_three = results[-3:]
    if all(last_three):
        return "Adaptive: 3 correct in a row — next question will increase in difficulty."
    if not any(last_three):
        return "Adaptive: 3 incorrect in a row — next question will decrease in difficulty."
    return "Adaptive: mixed recent results — difficulty stays the same for now."


def _clear_practice_question(question_id: str | None = None) -> None:
    if question_id:
        clear_shuffled_options(scoped_key(f"practice_opts_{question_id}"))
    scoped_pop("practice_current_question", None)
    scoped_pop("practice_feedback", None)


def _reset_practice_session() -> None:
    """Drop the in-progress queue so the next visit starts with fresh questions."""
    scoped_pop("practice_queue_key", None)
    scoped_pop("practice_question_queue", None)
    scoped_pop("practice_queue_index", None)
    _clear_practice_question()
    clear_scoped_prefix("practice_opts_")


def _advance_practice_queue() -> None:
    scoped_set("practice_queue_index", scoped_get("practice_queue_index", 0) + 1)


def _render_feedback(
    question: dict,
    feedback: dict,
    display_options: list[str],
) -> None:
    st.markdown('<div class="card question-card">', unsafe_allow_html=True)
    st.markdown(f"### {question.get('question_text', 'Question')}")
    if question.get("passage"):
        with st.expander("Passage"):
            st.write(question["passage"])
    render_answer_review(
        display_options,
        selected=feedback.get("selected"),
        correct=str(question.get("answer", "")),
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if feedback["is_correct"]:
        st.success("Correct!")
    else:
        st.error("Incorrect.")

    st.write(f"**Explanation:** {question['explanation']}")
    if question.get("strategy_tip"):
        st.write(f"**Strategy tip:** {question['strategy_tip']}")
    st.write(f"**Topic:** {question['topic']} | **Difficulty:** {question['difficulty']}")


def render():
    inject_compact_spacing()
    if returned_to_page("practice"):
        _reset_practice_session()

    st.title("Practice Questions")
    qs = QuestionService()
    active_batch = qs.get_active_student_batch_label()
    if not scoped_has("practice_results"):
        scoped_set("practice_results", [])
    if not scoped_has("adaptive_difficulty"):
        scoped_set("adaptive_difficulty", "Medium")

    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        exam_type = st.selectbox("Exam Type", ["SAT", "PSAT", "PSAT 8/9"])
    with filter_col2:
        subject = st.selectbox("Subject", ["Math", "Reading", "Writing"])
    if scoped_get("practice_subject") != subject:
        scoped_set("practice_subject", subject)
        clear_scoped_prefix("topics_")
        _clear_practice_question()

    topics = SUBJECT_TOPICS.get(
        subject,
        ["Algebra", "Geometry", "Vocabulary", "Grammar"],
    )
    with filter_col3:
        topic = st.selectbox("Topic", ["All"] + topics)

    settings_col1, settings_col2 = st.columns([1, 1])
    with settings_col1:
        difficulty_mode = st.toggle("Adaptive mode", value=True)
    with settings_col2:
        if not difficulty_mode:
            chosen_difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
        else:
            chosen_difficulty = scoped_get("adaptive_difficulty")

    filter_key = (active_batch, exam_type, subject, topic)
    topic_filter = None if topic == "All" else topic
    if scoped_get("practice_filter_key") != filter_key:
        scoped_set("practice_filter_key", filter_key)
        scoped_set("practice_results", [])
        scoped_set("adaptive_difficulty", "Medium")
        scoped_pop("practice_queue_key", None)
        scoped_pop("practice_question_queue", None)
        scoped_pop("practice_queue_index", None)
        _clear_practice_question()

    if difficulty_mode:
        prev_difficulty = scoped_get("practice_adaptive_difficulty")
        if prev_difficulty is not None and prev_difficulty != chosen_difficulty:
            scoped_pop("practice_queue_key", None)
            _clear_practice_question()
        scoped_set("practice_adaptive_difficulty", chosen_difficulty)
    else:
        prev_difficulty = scoped_get("practice_manual_difficulty")
        if prev_difficulty is not None and prev_difficulty != chosen_difficulty:
            scoped_pop("practice_queue_key", None)
            _clear_practice_question()
        scoped_set("practice_manual_difficulty", chosen_difficulty)

    pool_limit = PRACTICE_POOL_LIMIT
    count_key = (active_batch, exam_type, subject, topic_filter)
    if scoped_get("practice_count_key") != count_key:
        scoped_set("practice_count_key", count_key)
        scoped_set(
            "practice_total_available",
            qs.count_questions_for_students(
                exam_type=exam_type,
                subject=subject,
                topic=topic_filter,
            ),
        )
    total_available = scoped_get("practice_total_available", 0)
    if total_available == 0:
        st.info(
            "No questions found for selected filters. "
            "Run `python scripts/reload_exam_questions.py` or use Admin to download the question bank."
        )
        inject_ti84_cleanup(TI84_PAGE_KEYS)
        inject_dispute_modal_cleanup()
        return

    queue = _ensure_practice_queue(
        qs,
        filter_key=filter_key,
        exam_type=exam_type,
        subject=subject,
        topic=topic_filter,
        chosen_difficulty=chosen_difficulty,
        difficulty_mode=difficulty_mode,
        pool_limit=pool_limit,
    )
    if not queue:
        st.info("No questions match the current filters.")
        inject_ti84_cleanup(TI84_PAGE_KEYS)
        inject_dispute_modal_cleanup()
        return

    if not scoped_has("practice_current_question"):
        scoped_set("practice_current_question", _next_practice_question(queue))

    question = scoped_get("practice_current_question")
    if not question:
        st.info("No questions available.")
        inject_ti84_cleanup(TI84_PAGE_KEYS)
        inject_dispute_modal_cleanup()
        return

    question_batch = display_batch_label(question.get("source"))
    queue_position = scoped_get("practice_queue_index", 0) + 1
    meta_parts = [
        f"Batch: {question_batch}",
        f"Question {queue_position} of {len(queue)}",
        f"Difficulty: {question.get('difficulty', 'Unknown')}",
        f"Topic: {question.get('topic', '—')}",
    ]
    render_ti84_batch_row(
        " · ".join(meta_parts),
        page_key="practice",
        show_calculator=subject == "Math",
        button_key=scoped_key("practice_ti84_btn"),
    )
    if difficulty_mode:
        st.caption(
            f"Adaptive target: {chosen_difficulty} · "
            f"{_adaptive_status_message(scoped_get('practice_results', []))}"
        )

    display_options = shuffled_options(
        question,
        session_key=scoped_key(f"practice_opts_{question['question_id']}"),
    )
    feedback = scoped_get("practice_feedback")

    if feedback and feedback.get("question_id") == question["question_id"]:
        _render_feedback(question, feedback, display_options)

        user = st.session_state.get("auth_user")

        next_col, dispute_col = st.columns([1, 1])
        with next_col:
            if st.button("Next question", type="primary", key=scoped_key("practice_next_btn")):
                inject_dispute_modal_cleanup()
                scoped_pop(DISPUTE_OPEN_KEY, None)
                _advance_practice_queue()
                _clear_practice_question(question.get("question_id"))
                st.rerun()
        with dispute_col:
            if user and show_dispute_feedback_messages(
                user_id=user.id,
                question_id=question["question_id"],
            ):
                render_dispute_open_button(question["question_id"])

        if user:
            open_dispute_dialog_if_needed(
                question,
                user_id=user.id,
                feedback=feedback,
                display_options=display_options,
            )
    else:
        inject_dispute_modal_cleanup()
        scoped_pop(DISPUTE_OPEN_KEY, None)
        result = render_question_card(question, display_options=display_options)
        if result["submit"]:
            selected = result["selected_option"]
            if not selected:
                st.warning("Please select an answer before submitting.")
            else:
                is_correct = selected == question["answer"]
                scoped_set(
                    "practice_feedback",
                    {
                        "question_id": question["question_id"],
                        "selected": selected,
                        "is_correct": is_correct,
                    },
                )
                user = st.session_state.get("auth_user")
                if user:
                    qs.save_attempt(
                        user.id, question["question_id"], selected, is_correct, time_spent=60
                    )
                if difficulty_mode:
                    results = list(scoped_get("practice_results", []))
                    results.append(is_correct)
                    scoped_set("practice_results", results)
                    scoped_set(
                        "adaptive_difficulty",
                        next_difficulty(results, scoped_get("adaptive_difficulty")),
                    )
                st.rerun()

    with st.expander("Additional Details from Gemini"):
        if st.button("Generate AI Explanation"):
            try:
                gemini = GeminiService()
                with st.spinner("Generating explanation..."):
                    details = gemini.explain_question(
                        question["question_text"],
                        question["options"],
                        question["answer"],
                        question["explanation"],
                    )
                st.markdown(details)
            except Exception as exc:
                st.error(
                    "Unable to generate Gemini details right now. "
                    "Please verify GEMINI_API_KEY and OPENAI_MODEL in your .env."
                )
                st.caption(f"Technical details: {exc}")
