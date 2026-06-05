import random

import streamlit as st

from app.components.question_card import render_question_card
from app.services.adaptive_engine import next_difficulty
from app.services.gemini_service import GeminiService
from app.services.question_service import QuestionService
from app.utils.compact_layout import inject_compact_spacing
from app.utils.question_shuffle import clear_shuffled_options, shuffled_options, shuffle_questions


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
        pool = qs.get_questions(
            exam_type=exam_type,
            subject=subject,
            topic=topic,
            difficulty=chosen_difficulty,
            limit=pool_limit,
        )
        if not pool:
            pool = qs.get_questions(
                exam_type=exam_type,
                subject=subject,
                topic=topic,
                limit=pool_limit,
            )
    else:
        pool = qs.get_questions(
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
    if st.session_state.get("practice_queue_key") != queue_key:
        st.session_state["practice_queue_key"] = queue_key
        st.session_state["practice_question_queue"] = _build_practice_queue(
            qs,
            exam_type=exam_type,
            subject=subject,
            topic=topic,
            chosen_difficulty=chosen_difficulty,
            difficulty_mode=difficulty_mode,
            pool_limit=pool_limit,
        )
        st.session_state["practice_queue_index"] = 0
    return st.session_state.get("practice_question_queue", [])


def _next_practice_question(queue: list[dict]) -> dict | None:
    if not queue:
        return None
    index = st.session_state.get("practice_queue_index", 0)
    if index >= len(queue):
        random.shuffle(queue)
        st.session_state["practice_question_queue"] = queue
        index = 0
        st.session_state["practice_queue_index"] = 0
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
        clear_shuffled_options(f"practice_opts_{question_id}")
    st.session_state.pop("practice_current_question", None)
    st.session_state.pop("practice_feedback", None)


def _advance_practice_queue() -> None:
    st.session_state["practice_queue_index"] = st.session_state.get("practice_queue_index", 0) + 1


def _render_feedback(question: dict, feedback: dict) -> None:
    if feedback["is_correct"]:
        st.success("Correct!")
    else:
        st.error("Incorrect.")

    st.write(f"**Your answer:** {feedback['selected']}")
    st.write(f"**Correct answer:** {question['answer']}")
    st.write(f"**Explanation:** {question['explanation']}")
    st.write(f"**Strategy tip:** {question['strategy_tip']}")
    st.write(f"**Topic:** {question['topic']} | **Difficulty:** {question['difficulty']}")


def render():
    inject_compact_spacing()
    st.title("Practice Questions")
    qs = QuestionService()
    if "practice_results" not in st.session_state:
        st.session_state["practice_results"] = []
    if "adaptive_difficulty" not in st.session_state:
        st.session_state["adaptive_difficulty"] = "Medium"

    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        exam_type = st.selectbox("Exam Type", ["SAT", "PSAT", "PSAT 8/9"])
    with filter_col2:
        subject = st.selectbox("Subject", ["Math", "Reading", "Writing"])
    if st.session_state.get("practice_subject") != subject:
        st.session_state["practice_subject"] = subject
        for key in list(st.session_state.keys()):
            if key.startswith("topics_"):
                del st.session_state[key]
        _clear_practice_question()

    cache_key = f"topics_{subject}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = qs.topics_for_subject(subject) or [
            "Algebra",
            "Geometry",
            "Vocabulary",
            "Grammar",
        ]
    topics = st.session_state[cache_key]
    with filter_col3:
        topic = st.selectbox("Topic", ["All"] + topics)

    settings_col1, settings_col2 = st.columns([1, 1])
    with settings_col1:
        difficulty_mode = st.toggle("Adaptive mode", value=True)
    with settings_col2:
        if not difficulty_mode:
            chosen_difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
        else:
            chosen_difficulty = st.session_state["adaptive_difficulty"]

    filter_key = (exam_type, subject, topic)
    topic_filter = None if topic == "All" else topic
    if st.session_state.get("practice_filter_key") != filter_key:
        st.session_state["practice_filter_key"] = filter_key
        st.session_state["practice_results"] = []
        st.session_state["adaptive_difficulty"] = "Medium"
        st.session_state.pop("practice_queue_key", None)
        st.session_state.pop("practice_question_queue", None)
        st.session_state.pop("practice_queue_index", None)
        _clear_practice_question()

    if difficulty_mode:
        prev_difficulty = st.session_state.get("practice_adaptive_difficulty")
        if prev_difficulty is not None and prev_difficulty != chosen_difficulty:
            st.session_state.pop("practice_queue_key", None)
            _clear_practice_question()
        st.session_state["practice_adaptive_difficulty"] = chosen_difficulty
    else:
        prev_difficulty = st.session_state.get("practice_manual_difficulty")
        if prev_difficulty is not None and prev_difficulty != chosen_difficulty:
            st.session_state.pop("practice_queue_key", None)
            _clear_practice_question()
        st.session_state["practice_manual_difficulty"] = chosen_difficulty

    pool_limit = 10_000
    total_available = qs.count_questions(
        exam_type=exam_type,
        subject=subject,
        topic=topic_filter,
    )
    if total_available == 0:
        st.info(
            "No questions found for selected filters. "
            "Run `python scripts/reload_exam_questions.py` or use Admin to download the question bank."
        )
        return

    meta_parts = [
        f"{total_available} questions (shuffled)",
        f"Difficulty: {chosen_difficulty}",
    ]
    if difficulty_mode:
        meta_parts.append(_adaptive_status_message(st.session_state["practice_results"]))
    st.caption(" · ".join(meta_parts))

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
        return

    if "practice_current_question" not in st.session_state:
        st.session_state["practice_current_question"] = _next_practice_question(queue)

    question = st.session_state["practice_current_question"]
    if not question:
        st.info("No questions available.")
        return

    display_options = shuffled_options(question, session_key=f"practice_opts_{question['question_id']}")
    feedback = st.session_state.get("practice_feedback")

    if feedback and feedback.get("question_id") == question["question_id"]:
        st.markdown('<div class="card question-card">', unsafe_allow_html=True)
        st.markdown(f"### {question.get('question_text', 'Question')}")
        if question.get("passage"):
            with st.expander("Passage"):
                st.write(question["passage"])
        st.markdown("</div>", unsafe_allow_html=True)
        _render_feedback(question, feedback)

        if st.button("Next question", type="primary"):
            _advance_practice_queue()
            _clear_practice_question(question.get("question_id"))
            st.rerun()
    else:
        result = render_question_card(question, display_options=display_options)
        if result["submit"]:
            selected = result["selected_option"]
            if not selected:
                st.warning("Please select an answer before submitting.")
            else:
                is_correct = selected == question["answer"]
                st.session_state["practice_feedback"] = {
                    "question_id": question["question_id"],
                    "selected": selected,
                    "is_correct": is_correct,
                }
                user = st.session_state.get("auth_user")
                if user:
                    qs.save_attempt(
                        user.id, question["question_id"], selected, is_correct, time_spent=60
                    )
                if difficulty_mode:
                    st.session_state["practice_results"].append(is_correct)
                    st.session_state["adaptive_difficulty"] = next_difficulty(
                        st.session_state["practice_results"],
                        st.session_state["adaptive_difficulty"],
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

