import random

import streamlit as st

from app.components.question_card import render_question_card
from app.services.adaptive_engine import next_difficulty
from app.services.gemini_service import GeminiService
from app.services.question_service import QuestionService


def _pick_question(question_list: list[dict], chosen_difficulty: str) -> dict:
    matching = [q for q in question_list if q.get("difficulty") == chosen_difficulty]
    return random.choice(matching or question_list)


def _clear_practice_question() -> None:
    st.session_state.pop("practice_current_question", None)
    st.session_state.pop("practice_feedback", None)


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
    st.title("Practice Questions")
    qs = QuestionService()
    if "practice_results" not in st.session_state:
        st.session_state["practice_results"] = []
    if "adaptive_difficulty" not in st.session_state:
        st.session_state["adaptive_difficulty"] = "Medium"

    exam_type = st.selectbox("Exam Type", ["SAT", "PSAT", "PSAT 8/9"])
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
    topic = st.selectbox("Topic", ["All"] + topics)

    difficulty_mode = st.toggle("Adaptive mode", value=True)
    chosen_difficulty = (
        st.session_state["adaptive_difficulty"]
        if difficulty_mode
        else st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
    )
    st.caption(f"Current difficulty: {chosen_difficulty}")

    filter_key = (exam_type, subject, topic)
    if st.session_state.get("practice_filter_key") != filter_key:
        st.session_state["practice_filter_key"] = filter_key
        _clear_practice_question()

    pool_limit = 600 if topic == "All" and subject == "Math" else 200
    question_list = qs.get_questions(
        exam_type=exam_type,
        subject=subject,
        topic=None if topic == "All" else topic,
        limit=pool_limit,
    )

    if not question_list:
        st.info(
            "No questions found for selected filters. "
            "Run `python scripts/seed_bulk_questions.py` to load the practice bank."
        )
        return

    total_available = qs.count_questions(
        exam_type=exam_type,
        subject=subject,
        topic=None if topic == "All" else topic,
    )
    st.caption(f"{total_available} questions in bank for these filters")

    if "practice_current_question" not in st.session_state:
        st.session_state["practice_current_question"] = _pick_question(
            question_list, chosen_difficulty
        )

    question = st.session_state["practice_current_question"]
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
            _clear_practice_question()
            st.rerun()
    else:
        result = render_question_card(question)
        if result["submit"]:
            selected = result["selected_option"]
            if not selected:
                st.warning("Please select an answer before submitting.")
            else:
                is_correct = selected == question["answer"]
                st.session_state["practice_results"].append(is_correct)
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
