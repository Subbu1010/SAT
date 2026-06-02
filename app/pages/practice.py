import streamlit as st

from app.components.question_card import render_question_card
from app.services.adaptive_engine import next_difficulty
from app.services.gemini_service import GeminiService
from app.services.question_service import QuestionService


def render():
    st.title("Practice Questions")
    qs = QuestionService()
    if "practice_results" not in st.session_state:
        st.session_state["practice_results"] = []
    if "adaptive_difficulty" not in st.session_state:
        st.session_state["adaptive_difficulty"] = "Medium"

    exam_type = st.selectbox("Exam Type", ["SAT", "PSAT", "PSAT 8/9"])
    subject = st.selectbox("Subject", ["Math", "Reading", "Writing"])
    topics = qs.topics_for_subject(subject) or ["Algebra", "Geometry", "Vocabulary", "Grammar"]
    topic = st.selectbox("Topic", ["All"] + topics)

    difficulty_mode = st.toggle("Adaptive mode", value=True)
    chosen_difficulty = (
        st.session_state["adaptive_difficulty"]
        if difficulty_mode
        else st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
    )
    st.caption(f"Current difficulty: {chosen_difficulty}")

    question_list = qs.get_questions(
        exam_type=exam_type,
        subject=subject,
        difficulty=chosen_difficulty,
        topic=None if topic == "All" else topic,
        limit=1,
    )

    if not question_list:
        st.info("No questions found for selected filters.")
        return

    question = question_list[0]
    result = render_question_card(question)
    if result["submit"]:
        selected = result["selected_option"]
        is_correct = selected == question["answer"]
        st.session_state["practice_results"].append(is_correct)
        user = st.session_state.get("auth_user")
        if user:
            qs.save_attempt(user.id, question["question_id"], selected, is_correct, time_spent=60)
        st.success("Correct!" if is_correct else "Not quite. Keep going.")
        st.write(f"Correct Answer: {question['answer']}")
        st.write(f"Explanation: {question['explanation']}")
        st.write(f"Strategy Tip: {question['strategy_tip']}")
        st.write(f"Topic: {question['topic']} | Difficulty: {question['difficulty']}")

        st.session_state["adaptive_difficulty"] = next_difficulty(
            st.session_state["practice_results"], st.session_state["adaptive_difficulty"]
        )

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
