import streamlit as st

from app.components.answer_selector import render_answer_selector
from app.utils.scoped_session import scoped_key


def render_question_card(
    question: dict,
    display_options: list[str] | None = None,
):
    st.markdown('<div class="card question-card">', unsafe_allow_html=True)
    st.markdown(f"### {question.get('question_text', 'Question')}")
    if question.get("passage"):
        with st.expander("Passage"):
            st.write(question["passage"])

    options = display_options if display_options is not None else question.get("options", [])
    qid = question.get("question_id", "unknown")
    option = render_answer_selector(
        [str(opt) for opt in options if str(opt).strip()],
        widget_key=scoped_key(f"practice_ans_{qid}"),
    )

    submit = st.button("Submit", key=scoped_key(f"practice_submit_{qid}"))
    st.markdown("</div>", unsafe_allow_html=True)
    return {"selected_option": option, "submit": submit}
