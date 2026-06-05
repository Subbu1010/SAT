import streamlit as st


def render_question_card(question: dict):
    st.markdown('<div class="card question-card">', unsafe_allow_html=True)
    st.markdown(f"### {question.get('question_text', 'Question')}")
    if question.get("passage"):
        with st.expander("Passage"):
            st.write(question["passage"])

    options = question.get("options", [])
    option = None
    if options:
        option = st.radio(
            "Choose your answer",
            options,
            key=f"q_option_{question.get('question_id')}",
            index=None,
        )

    submit = st.button("Submit", key=f"submit_{question.get('question_id')}")
    st.markdown("</div>", unsafe_allow_html=True)
    return {"selected_option": option, "submit": submit}
