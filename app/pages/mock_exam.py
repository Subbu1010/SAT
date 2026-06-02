import time

import streamlit as st


def render():
    st.title("Timed Mock Exam")
    if "exam_running" not in st.session_state:
        st.session_state["exam_running"] = False
        st.session_state["exam_end_ts"] = None
        st.session_state["exam_duration"] = 60 * 60

    c1, c2, c3 = st.columns(3)
    if c1.button("Start Test"):
        st.session_state["exam_running"] = True
        st.session_state["exam_end_ts"] = time.time() + st.session_state["exam_duration"]
    if c2.button("Pause"):
        st.session_state["exam_running"] = False
    if c3.button("End Test"):
        st.session_state["exam_running"] = False
        st.success("Exam ended. Score: 1280 | Accuracy: 78% | Time Taken: 58m")

    if st.session_state["exam_running"] and st.session_state["exam_end_ts"]:
        remaining = max(0, int(st.session_state["exam_end_ts"] - time.time()))
        progress = 1 - (remaining / st.session_state["exam_duration"])
        st.progress(progress, text=f"Time remaining: {remaining // 60:02d}:{remaining % 60:02d}")
        st.caption("Question Navigator | Flagged Questions | Remaining Questions")
