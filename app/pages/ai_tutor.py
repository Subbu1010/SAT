import streamlit as st

from app.services.gemini_service import GeminiService
from app.services.rag_service import RAGService


def render():
    st.title("AI Tutor")
    st.caption("Context-aware SAT/PSAT tutoring with RAG + Gemini.")
    if "tutor_messages" not in st.session_state:
        st.session_state["tutor_messages"] = []

    for msg in st.session_state["tutor_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Ask about concepts, strategies, or question solving...")
    if prompt:
        st.session_state["tutor_messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        rag = RAGService()
        context = rag.retrieve_context(prompt)
        gemini = GeminiService()

        with st.chat_message("assistant"):
            holder = st.empty()
            full = ""
            for token in gemini.stream_tutor_response(prompt, context=context):
                full += token
                holder.markdown(full)
        st.session_state["tutor_messages"].append({"role": "assistant", "content": full})
