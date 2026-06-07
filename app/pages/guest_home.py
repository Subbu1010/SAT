"""Public landing page — infographic-style SAT overview for guests."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import streamlit as st

from app.pages.landing_svg import (
    adaptive_flow_svg,
    content_donut_svg,
    hero_device_svg,
    scoring_gauge_svg,
    structure_timeline_svg,
)
from app.utils.compact_layout import inject_compact_spacing

_RW_SEGMENTS = [
    ("Craft and Structure", 28, "#2d7ff9"),
    ("Information and Ideas", 26, "#5ba0ff"),
    ("Standard English Conventions", 26, "#1262e0"),
    ("Expression of Ideas", 20, "#8ec0ff"),
]
_MATH_SEGMENTS = [
    ("Algebra", 35, "#1b9c6e"),
    ("Advanced Math", 35, "#34c38f"),
    ("Problem Solving & Data", 15, "#0d5c41"),
    ("Geometry & Trigonometry", 15, "#7ee0b8"),
]

_RESOURCES = [
    (
        "https://satsuite.collegeboard.org/sat/whats-on-the-test/structure",
        "🎓",
        "College Board",
        "Official SAT structure, timing, and adaptive testing overview.",
    ),
    (
        "https://testinnovators.com/sat/about-the-sat/",
        "📊",
        "Test Innovators",
        "SAT format infographic, scoring explainer, and prep guidance.",
    ),
    (
        "https://www.khanacademy.org/sat",
        "📚",
        "Khan Academy",
        "Free Official SAT Prep with practice tailored to your level.",
    ),
    (
        "https://satsuite.collegeboard.org/digital",
        "💻",
        "Bluebook App",
        "College Board's digital testing app — device requirements and features.",
    ),
]

_FAQ_ITEMS = [
    (
        "Is the SAT adaptive?",
        "Yes. The digital SAT is section-adaptive (multistage adaptive). Each section has two "
        "modules; your performance in Module 1 determines whether Module 2 is easier or more "
        "challenging. Questions within a module are fixed — you can move freely within the "
        "module but cannot return to a previous one.",
    ),
    (
        "How is the SAT scored?",
        "The SAT uses Item Response Theory (IRT): harder questions carry more weight. Raw "
        "performance is equated across test forms, then converted to section scores of "
        "200–800 (Reading & Writing and Math), combined for 400–1600 total.",
    ),
    (
        "How long is the test?",
        "2 hours and 14 minutes of active testing (98 questions), plus a 10-minute break "
        "between Reading & Writing and Math.",
    ),
    (
        "What question types appear?",
        "Reading & Writing: multiple choice with short passages (25–150 words). Math: ~75% "
        "multiple choice and ~25% student-produced response (grid-in). Calculators are "
        "allowed for the entire Math section.",
    ),
    (
        "What's the best way to prepare?",
        "Take a full-length practice test, review results to find skill gaps, then practice "
        "those weak areas — and repeat. Consistent, focused practice beats cramming.",
    ),
]


def _load_landing_css() -> str:
    css_path = Path(__file__).resolve().parent.parent / "styles" / "landing.css"
    return css_path.read_text(encoding="utf-8")


def _faq_html() -> str:
    items = []
    for question, answer in _FAQ_ITEMS:
        items.append(
            f"<details><summary>{question}</summary>"
            f'<div class="faq-body">{answer}</div></details>'
        )
    return f'<div class="landing-faq">{"".join(items)}</div>'


def _resources_html() -> str:
    cards = []
    for url, icon, title, desc in _RESOURCES:
        cards.append(
            f'<a class="landing-resource" href="{url}" target="_blank" rel="noopener noreferrer">'
            f'<span class="res-icon">{icon}</span>'
            f'<span class="res-title">{title}</span>'
            f'<span class="res-desc">{desc}</span></a>'
        )
    return f'<div class="landing-resource-grid">{"".join(cards)}</div>'


def _build_landing_html() -> str:
    """Assemble the full landing page HTML (flush-left to avoid markdown code blocks)."""
    rw_donut = content_donut_svg(_RW_SEGMENTS, title="Reading and Writing domains", center_label="R&W")
    math_donut = content_donut_svg(_MATH_SEGMENTS, title="Math domains", center_label="Math")

    return dedent(
        f"""
        <style>{_load_landing_css()}</style>
        <div class="landing-page">
          <section class="landing-hero-banner">
            <div>
              <p class="landing-kicker">About the Digital SAT</p>
              <h1>Here's what you need to know</h1>
              <p class="lead">
                Get up to speed on the SAT's digital adaptive format, content, and scoring —
                then <strong>sign in from the sidebar</strong> to start adaptive practice,
                timed mock exams, analytics, and AI tutoring on this platform.
              </p>
              <div class="landing-hero-badges">
                <span class="landing-badge">💻 Computer-based</span>
                <span class="landing-badge">🎯 Section-adaptive</span>
                <span class="landing-badge">📱 Bluebook app</span>
                <span class="landing-badge">🧮 Desmos calculator</span>
              </div>
            </div>
            <div>{hero_device_svg().strip()}</div>
          </section>

          <div class="landing-stat-grid">
            <div class="landing-stat"><span class="icon">⏱️</span><span class="value">2h 14m</span><span class="label">Total testing time</span></div>
            <div class="landing-stat"><span class="icon">📝</span><span class="value">98</span><span class="label">Total questions</span></div>
            <div class="landing-stat"><span class="icon">🎯</span><span class="value">400–1600</span><span class="label">Total score range</span></div>
            <div class="landing-stat"><span class="icon">📅</span><span class="value">8×</span><span class="label">Test dates per year</span></div>
          </div>

          <div class="landing-section-head">
            <h2>SAT Structure, Format, and Content</h2>
            <p>The SAT is a computer-based, adaptive test with two sections — administered via College Board's Bluebook app.</p>
          </div>
          <div class="landing-panel">{structure_timeline_svg().strip()}</div>

          <div class="landing-format-grid">
            <div class="landing-format-card">
              <div class="card-icon">💻</div>
              <h4>Test Format</h4>
              <p>Administered on computer using the Bluebook testing application.</p>
              <span class="highlight">Digital</span>
            </div>
            <div class="landing-format-card">
              <div class="card-icon">🔀</div>
              <h4>Section Adaptive</h4>
              <p>Module 2 difficulty depends on your Module 1 performance in each section.</p>
              <span class="highlight">2 modules</span>
            </div>
            <div class="landing-format-card">
              <div class="card-icon">✅</div>
              <h4>Multiple Choice</h4>
              <p>Four answer choices on most questions across both sections.</p>
              <span class="highlight">4 choices</span>
            </div>
            <div class="landing-format-card">
              <div class="card-icon">✏️</div>
              <h4>Student-Produced Response</h4>
              <p>Grid-in answers on ~25% of Math questions — enter your own answer.</p>
              <span class="highlight">Math only</span>
            </div>
            <div class="landing-format-card">
              <div class="card-icon">⏳</div>
              <h4>Time Per Question</h4>
              <p>Reading &amp; Writing averages ~71 seconds; Math averages ~95 seconds.</p>
              <span class="highlight">71s / 95s</span>
            </div>
            <div class="landing-format-card">
              <div class="card-icon">🧮</div>
              <h4>Calculator</h4>
              <p>Allowed on the entire Math section — bring approved or use built-in Desmos.</p>
              <span class="highlight">Desmos</span>
            </div>
          </div>

          <div class="landing-panel">{adaptive_flow_svg().strip()}</div>

          <div class="landing-section-head">
            <h2>Content Domains</h2>
            <p>What skills each section measures — based on College Board and Test Innovators breakdowns.</p>
          </div>
          <div class="landing-split">
            <div class="landing-split-card rw">
              <h3>📖 Reading &amp; Writing</h3>
              <p class="meta">64 min · 54 questions · Passages 25–150 words per question</p>
              <div class="landing-module-row">
                <div class="landing-mod"><strong>Module 1</strong><span>32 min · 27 Qs</span></div>
                <div class="landing-mod"><strong>Module 2</strong><span>Adaptive difficulty</span></div>
              </div>
              {rw_donut}
            </div>
            <div class="landing-split-card math">
              <h3>🔢 Math</h3>
              <p class="meta">70 min · 44 questions · Increasing difficulty within modules</p>
              <div class="landing-module-row">
                <div class="landing-mod"><strong>Module 1</strong><span>35 min · 22 Qs</span></div>
                <div class="landing-mod"><strong>Module 2</strong><span>Adaptive difficulty</span></div>
              </div>
              {math_donut}
            </div>
          </div>

          <div class="landing-panel">
            <h3>Scoring</h3>
            <p class="panel-sub">Item Response Theory (IRT) weights questions by difficulty — equating ensures fair scores across test forms.</p>
            {scoring_gauge_svg().strip()}
          </div>
          <div class="landing-panel">
            <h3>2025–26 Test Dates</h3>
            <p class="panel-sub">SAT is offered eight times per year (international and U.S. schedules may vary).</p>
            <div class="landing-dates">
              <span class="landing-date-pill">March</span>
              <span class="landing-date-pill">May</span>
              <span class="landing-date-pill">June</span>
              <span class="landing-date-pill">August</span>
              <span class="landing-date-pill">September</span>
              <span class="landing-date-pill">October</span>
              <span class="landing-date-pill">November</span>
              <span class="landing-date-pill">December</span>
            </div>
          </div>

          <div class="landing-section-head">
            <h2>How to Prepare Effectively</h2>
            <p>A repeatable cycle recommended by Test Innovators and College Board.</p>
          </div>
          <div class="landing-steps">
            <div class="landing-step">
              <span class="step-num">1</span>
              <h4>Take a practice test</h4>
              <p>Establish a baseline with a full-length timed mock under real conditions.</p>
            </div>
            <div class="landing-step">
              <span class="step-num">2</span>
              <h4>Review your results</h4>
              <p>Identify patterns — which topics, question types, and difficulty levels need work.</p>
            </div>
            <div class="landing-step">
              <span class="step-num">3</span>
              <h4>Target weak areas</h4>
              <p>Practice adaptively, revisit explanations, and repeat the cycle until test day.</p>
            </div>
          </div>

          <div class="landing-section-head">
            <h2>Top Questions About the SAT</h2>
            <p>Answers to common questions students and families ask.</p>
          </div>
          {_faq_html()}

          <div class="landing-section-head">
            <h2>Trusted SAT Resources</h2>
            <p>Explore official and expert guides to deepen your understanding.</p>
          </div>
          {_resources_html()}

          <section class="landing-cta">
            <h2>Ready to start practicing?</h2>
            <p>
              Sign in from the <strong>sidebar</strong> to unlock this platform's adaptive
              question bank, timed mock exams, performance analytics, and AI tutor —
              built for SAT Math, Reading, and Writing.
            </p>
            <div class="landing-features">
              <div class="landing-feature"><span class="feat-icon">✏️</span><strong>Adaptive Practice</strong><span>Difficulty adjusts to you</span></div>
              <div class="landing-feature"><span class="feat-icon">⏱️</span><strong>Timed Mock Exams</strong><span>Real test-day conditions</span></div>
              <div class="landing-feature"><span class="feat-icon">📈</span><strong>Analytics</strong><span>Track progress by topic</span></div>
              <div class="landing-feature"><span class="feat-icon">🤖</span><strong>AI Tutor</strong><span>Explanations on demand</span></div>
            </div>
            <span class="cta-arrow">← Sign in from the sidebar to begin</span>
          </section>
          <p class="landing-footer">
            Content informed by
            <a href="https://testinnovators.com/sat/about-the-sat/" target="_blank" rel="noopener noreferrer">Test Innovators</a>,
            <a href="https://satsuite.collegeboard.org/sat/whats-on-the-test/structure" target="_blank" rel="noopener noreferrer">College Board SAT Suite</a>,
            and <a href="https://www.khanacademy.org/sat" target="_blank" rel="noopener noreferrer">Khan Academy Official SAT Prep</a>.
            SAT® is a trademark registered by College Board.
          </p>
        </div>
        """
    ).strip()


def render() -> None:
    inject_compact_spacing()
    st.html(_build_landing_html())
