import streamlit as st


def render_stat_card(title: str, value: str, trend: str = ""):
    st.markdown(
        f"""
        <div class="card stat-card">
            <div class="stat-title">{title}</div>
            <div class="stat-value">{value}</div>
            <div class="stat-trend">{trend}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
