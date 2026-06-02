import pandas as pd
import plotly.express as px
import streamlit as st

from app.components.stat_card import render_stat_card


def render():
    st.title("Student Dashboard")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_stat_card("Total Questions Attempted", "284", "+14 this week")
    with c2:
        render_stat_card("Accuracy Percentage", "81%", "+3.2%")
    with c3:
        render_stat_card("Average Score", "1320", "+40")
    with c4:
        render_stat_card("Current Streak", "7 days", "Keep going")

    sample_week = pd.DataFrame(
        {
            "day": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "questions": [22, 18, 31, 25, 27, 35, 20],
        }
    )
    sample_month = pd.DataFrame(
        {
            "week": ["W1", "W2", "W3", "W4"],
            "score": [1210, 1250, 1290, 1320],
        }
    )

    st.subheader("Weekly Activity")
    st.plotly_chart(px.bar(sample_week, x="day", y="questions"), use_container_width=True)

    st.subheader("Monthly Progress")
    st.plotly_chart(px.line(sample_month, x="week", y="score", markers=True), use_container_width=True)
