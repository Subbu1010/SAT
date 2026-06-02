import streamlit as st


def render_question_card(question: dict):
    st.markdown('<div class="card question-card">', unsafe_allow_html=True)
    st.markdown(f"### {question.get('question_text', 'Question')}")
    if question.get("passage"):
        with st.expander("Passage"):
            st.write(question["passage"])
    option = st.radio(
        "Choose your answer",
        question.get("options", []),
        key=f"q_option_{question.get('question_id')}",
    )
    col1, col2, col3 = st.columns(3)
    submit = col1.button("Submit", key=f"submit_{question.get('question_id')}")
    save = col2.button("Save for Later", key=f"save_{question.get('question_id')}")
    flag = col3.button("Flag", key=f"flag_{question.get('question_id')}")
    st.markdown("</div>", unsafe_allow_html=True)
    return {"selected_option": option, "submit": submit, "save": save, "flag": flag}
