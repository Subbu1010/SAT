import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def render():
    st.title("Performance Analytics")
    perf = pd.DataFrame(
        {
            "topic": ["Algebra", "Geometry", "Trigonometry", "Grammar", "Reading"],
            "accuracy": [85, 74, 69, 88, 79],
            "time_spent": [120, 95, 80, 70, 110],
        }
    )
    st.plotly_chart(px.bar(perf, x="topic", y="accuracy", color="accuracy"), use_container_width=True)
    st.plotly_chart(px.line(perf, x="topic", y="time_spent", markers=True), use_container_width=True)

    radar = go.Figure(
        data=go.Scatterpolar(
            r=perf["accuracy"],
            theta=perf["topic"],
            fill="toself",
            name="Topic Accuracy",
        )
    )
    radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), showlegend=False)
    st.plotly_chart(radar, use_container_width=True)
