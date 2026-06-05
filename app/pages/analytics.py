import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.authentication.auth_service import AuthService
from app.services.analytics_service import get_performance_analytics


def render():
    st.title("Performance Analytics")
    auth = AuthService()
    user = auth.current_user()
    if not user:
        st.info("Please log in to view your analytics.")
        return

    data = get_performance_analytics(user.id)
    if not data["has_data"]:
        st.info(
            "No performance data yet. Complete practice questions or mock exams "
            "to see your analytics here."
        )
        return

    topic_perf = data["topic_performance"]
    if not topic_perf.empty:
        st.subheader("Accuracy by topic")
        st.plotly_chart(
            px.bar(
                topic_perf,
                x="topic",
                y="accuracy",
                color="accuracy",
                color_continuous_scale="Blues",
                labels={"accuracy": "Accuracy %", "topic": "Topic"},
                text="accuracy",
            ).update_traces(texttemplate="%{text:.1f}%", textposition="outside"),
            use_container_width=True,
        )

        st.subheader("Average time per topic")
        st.plotly_chart(
            px.line(
                topic_perf,
                x="topic",
                y="time_spent",
                markers=True,
                labels={"time_spent": "Avg time (seconds)", "topic": "Topic"},
            ),
            use_container_width=True,
        )

        st.subheader("Topic strength overview")
        radar = go.Figure(
            data=go.Scatterpolar(
                r=topic_perf["accuracy"],
                theta=topic_perf["topic"],
                fill="toself",
                name="Topic accuracy",
            )
        )
        radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False,
        )
        st.plotly_chart(radar, use_container_width=True)

        with st.expander("Topic details"):
            st.dataframe(
                topic_perf.rename(
                    columns={
                        "topic": "Topic",
                        "accuracy": "Accuracy %",
                        "time_spent": "Avg time (s)",
                        "attempts": "Attempts",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.caption("No practice attempts yet. Topic charts will appear after you practice.")

    subject_perf = data["subject_performance"]
    if not subject_perf.empty:
        st.subheader("Accuracy by subject")
        st.plotly_chart(
            px.bar(
                subject_perf,
                x="subject",
                y="accuracy",
                color="subject",
                labels={"accuracy": "Accuracy %", "subject": "Subject"},
                text="accuracy",
            ).update_traces(texttemplate="%{text:.1f}%", textposition="outside"),
            use_container_width=True,
        )

    difficulty_perf = data["difficulty_performance"]
    if not difficulty_perf.empty:
        st.subheader("Accuracy by difficulty")
        st.plotly_chart(
            px.bar(
                difficulty_perf,
                x="difficulty",
                y="accuracy",
                color="difficulty",
                labels={"accuracy": "Accuracy %", "difficulty": "Difficulty"},
                text="accuracy",
            ).update_traces(texttemplate="%{text:.1f}%", textposition="outside"),
            use_container_width=True,
        )

    exam_history = data["exam_history"]
    if not exam_history.empty:
        st.subheader("Mock exam scores over time")
        st.plotly_chart(
            px.line(
                exam_history,
                x="exam",
                y="score",
                markers=True,
                labels={"score": "SAT points earned", "exam": "Mock exam"},
            ),
            use_container_width=True,
        )
        with st.expander("Mock exam history"):
            st.dataframe(
                exam_history.rename(
                    columns={
                        "exam": "Exam",
                        "score": "SAT score",
                        "accuracy": "Accuracy %",
                        "completed_at": "Completed at",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
    elif data["total_attempts"]:
        st.caption("Complete a mock exam to see score trends.")
