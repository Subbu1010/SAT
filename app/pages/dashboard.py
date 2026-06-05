import plotly.express as px
import streamlit as st

from app.authentication.auth_service import AuthService
from app.components.stat_card import render_stat_card
from app.services.dashboard_service import get_dashboard_stats


def render():
    st.title("Student Dashboard")
    auth = AuthService()
    user = auth.current_user()
    if not user:
        st.info("Please log in to view your dashboard.")
        return

    stats = get_dashboard_stats(user.id)

    if not stats["has_data"]:
        st.info(
            "No activity yet. Complete practice questions or a mock exam to see your stats here."
        )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_stat_card(
            "Total Questions Attempted",
            str(stats["total_attempted"]),
            (
                f"{stats['practice_attempted']} practice + {stats['mock_questions']} mock · "
                f"{stats['attempts_delta']:+d} this week"
            ),
        )
    with c2:
        accuracy_trend = (
            f"{stats['accuracy_delta']:+.1f}% vs last week"
            if stats["accuracy_delta"] is not None
            else "Practice more to track trend"
        )
        render_stat_card(
            "Accuracy Percentage",
            f"{stats['accuracy']:.0f}%",
            accuracy_trend,
        )
    with c3:
        avg_score = stats["avg_score"]
        score_trend = (
            f"{stats['score_delta']:+d} vs previous exam"
            if stats["score_delta"] is not None
            else "Complete a mock exam"
        )
        render_stat_card(
            "Average Mock Score",
            str(avg_score) if avg_score is not None else "—",
            score_trend,
        )
    with c4:
        streak = stats["streak"]
        streak_trend = "Keep going!" if streak else "Start your streak today"
        render_stat_card(
            "Current Streak",
            f"{streak} day{'s' if streak != 1 else ''}",
            streak_trend,
        )

    st.subheader("Weekly Activity")
    weekly = stats["weekly_activity"]
    if weekly["questions"].sum() == 0:
        st.caption("No practice or mock exam activity in the last 7 days.")
    st.plotly_chart(
        px.bar(
            weekly,
            x="day",
            y="questions",
            labels={"questions": "Questions attempted"},
        ),
        use_container_width=True,
    )
    if weekly["mock"].sum() > 0:
        st.caption("Weekly activity includes practice questions and mock exam questions answered.")

    st.subheader("Monthly Progress")
    monthly = stats["monthly_progress"]
    if monthly["score"].notna().any():
        chart_df = monthly.dropna(subset=["score"])
        uses_accuracy = (chart_df["metric"] == "accuracy").any() and not (
            chart_df["metric"] == "score"
        ).any()
        y_label = "Accuracy %" if uses_accuracy else "Mock exam score"
        st.plotly_chart(
            px.line(
                chart_df,
                x="week",
                y="score",
                markers=True,
                labels={"score": y_label},
            ),
            use_container_width=True,
        )
        if (monthly["metric"] == "accuracy").any() and (monthly["metric"] == "score").any():
            st.caption("Weeks with mock exams show average score; other weeks show practice accuracy.")
    else:
        st.caption("No mock exams or practice accuracy data for the last 4 weeks.")
