import streamlit as st

from app.services.gemini_service import GeminiService
from app.services.rag_service import RAGService
from app.utils.compact_layout import inject_compact_spacing

SUGGESTED_PROMPTS = [
    "Explain how to solve linear equations for SAT Math.",
    "What is the best strategy for SAT Reading comprehension?",
    "How do I improve grammar questions on the PSAT?",
    "Give me a 7-day SAT study plan.",
]


def _stream_gemini_response(gemini: GeminiService, prompt: str, context: str, holder) -> str:
    full = ""
    holder.markdown('<p class="tutor-typing">Gemini is thinking...</p>', unsafe_allow_html=True)

    try:
        for token in gemini.stream_tutor_response(prompt, context=context):
            full += token
            holder.markdown(full)
    except Exception:
        full = gemini.tutor_reply(prompt, context=context)
        holder.markdown(full)

    return full


def render():
    inject_compact_spacing()
    st.title("AI Tutor")
    st.caption("Powered by Gemini (gemini-2.5-pro) with optional RAG context.")

    if "tutor_messages" not in st.session_state:
        st.session_state["tutor_messages"] = []

    st.caption("Suggested prompts")
    cols = st.columns(4)
    for i, suggestion in enumerate(SUGGESTED_PROMPTS):
        if cols[i].button(suggestion, key=f"suggest_{i}", use_container_width=True):
            st.session_state["tutor_pending_prompt"] = suggestion

    for msg in st.session_state["tutor_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    pending = st.session_state.pop("tutor_pending_prompt", None)
    prompt = pending or st.chat_input("Ask about concepts, strategies, or question solving...")

    if not prompt:
        return

    st.session_state["tutor_messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        with st.status("Preparing AI Tutor response...", expanded=True) as status:
            status.write("Step 1/3: Understanding your question...")
            context = ""
            try:
                status.update(label="Retrieving study context...", state="running")
                status.write("Step 2/3: Searching relevant SAT/PSAT material...")
                context = RAGService().retrieve_context(prompt)
                if context.strip():
                    status.write("Related study context found.")
                else:
                    status.write("No extra context found — using Gemini directly.")
            except Exception:
                status.write("Context search skipped — using Gemini directly.")

            status.update(label="Waiting for Gemini...", state="running")
            status.write("Step 3/3: Gemini is generating your answer...")
            gemini = GeminiService()

        with st.chat_message("assistant"):
            holder = st.empty()
            full = _stream_gemini_response(gemini, prompt, context, holder)

        if full.strip():
            st.session_state["tutor_messages"].append({"role": "assistant", "content": full})
        else:
            st.error("Gemini returned an empty response. Check GEMINI_API_KEY and GEMINI_MODEL in .env.")
    except Exception as exc:
        st.error("AI Tutor could not reach Gemini.")
        st.caption(
            "Verify `.env` has:\n"
            "- `GEMINI_API_KEY`\n"
            "- `GEMINI_MODEL=gemini-2.5-pro`\n"
            "- `GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/`"
        )
        st.caption(f"Details: {exc}")
