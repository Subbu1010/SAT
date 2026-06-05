"""
Forum-source verification for SAT/PSAT practice questions.

After reviewing public forums (Reddit r/SAT, Discord, Telegram) and tutor recap
blogs that compile forum discussions, forum-posted items are not imported unless
they pass every verification gate below.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.database.official_loaders.validation import (
    ALL_EXAM_TYPES,
    dedupe_rows,
    is_valid_question_row,
    question_fingerprint,
)

FORUM_SOURCE = "forum_verified"
MIN_EXPLANATION_LENGTH = 50
MIN_CONSENSUS_SOURCES = 2

# Public forum research summary (2025–2026).
FORUM_SOURCE_ASSESSMENTS = [
    {
        "name": "Reddit r/SAT megathreads",
        "url": "https://www.reddit.com/r/SAT/",
        "verdict": "reject",
        "reason": (
            "Post-test threads contain memory reconstructions, debated answers, and "
            "incomplete stems. College Board does not release official keys for live tests."
        ),
    },
    {
        "name": "Discord / Telegram 'SAT leak' channels",
        "url": "N/A",
        "verdict": "reject",
        "reason": (
            "Digital SAT uses adaptive unique forms; 'leaks' are usually recycled Bluebook "
            "content or scams. Sharing live items violates College Board test security rules."
        ),
    },
    {
        "name": "Tutor blogs compiling Reddit discussions",
        "url": "https://thetestadvantage.com/blog/",
        "verdict": "reject",
        "reason": (
            "Articles transcribe live-test items from forums for commentary. They are not "
            "licensed for redistribution and disclaim being non-official materials."
        ),
    },
    {
        "name": "OpenSAT community JSON (GitHub / jsonsilo)",
        "url": "https://github.com/Anas099X/OpenSAT",
        "verdict": "accepted",
        "reason": (
            "Structured digital SAT format with four choices, explanations, and domains. "
            "Loaded separately as opensat_community after schema validation."
        ),
    },
    {
        "name": "College Board Educator Question Bank",
        "url": "https://satsuiteeducatorquestionbank.collegeboard.org/",
        "verdict": "manual_only",
        "reason": "Official items exist but export is PDF-only (no public API). Use Admin CSV import.",
    },
]


@dataclass
class ForumVerificationReport:
    candidates_reviewed: int = 0
    accepted: int = 0
    rejected: int = 0
    rejection_reasons: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def reject(self, reason: str) -> None:
        self.rejected += 1
        self.rejection_reasons[reason] = self.rejection_reasons.get(reason, 0) + 1

    def summary(self) -> str:
        if self.accepted == 0:
            return (
                f"Forum review: {self.candidates_reviewed} candidates, "
                f"0 imported (all failed verification). "
                f"Top rejections: {self._top_reasons()}."
            )
        return (
            f"Forum review: {self.candidates_reviewed} candidates, "
            f"{self.accepted} imported, {self.rejected} rejected."
        )

    def _top_reasons(self) -> str:
        if not self.rejection_reasons:
            return "none"
        ordered = sorted(self.rejection_reasons.items(), key=lambda item: item[1], reverse=True)
        return "; ".join(f"{reason} ({count})" for reason, count in ordered[:3])


def _has_four_distinct_options(options: list[str]) -> bool:
    cleaned = [opt.strip().lower() for opt in options if opt.strip()]
    return len(cleaned) == 4 and len(set(cleaned)) == 4


def verify_forum_candidate(
    candidate: dict[str, Any],
    *,
    existing_fingerprints: set[str] | None = None,
    consensus_sources: int = 1,
) -> tuple[bool, str]:
    """
    Strict gate for forum-sourced candidates.

    Requires:
    - Complete digital SAT MCQ structure (4 options, answer in options)
    - Explanation long enough to justify the keyed answer
    - At least two independent public sources agreeing (forum posts alone do not qualify)
    - Not a duplicate of an existing bank row
    """
    if consensus_sources < MIN_CONSENSUS_SOURCES:
        return False, "insufficient_consensus_sources"

    if not _has_four_distinct_options(candidate.get("options") or []):
        return False, "invalid_or_incomplete_options"

    if len(str(candidate.get("explanation") or "").strip()) < MIN_EXPLANATION_LENGTH:
        return False, "explanation_too_short_for_verification"

    if str(candidate.get("provenance") or "").lower() in {
        "reddit_memory",
        "discord",
        "telegram",
        "leak",
        "transcribed_live_test",
    }:
        return False, "unauthorized_or_unverifiable_provenance"

    if not is_valid_question_row(candidate):
        return False, "failed_schema_validation"

    fingerprint = question_fingerprint(candidate)
    if existing_fingerprints and fingerprint in existing_fingerprints:
        return False, "duplicate_of_existing_bank"

    return True, "verified"


def _forum_review_candidates() -> list[dict[str, Any]]:
    """
    Representative forum-derived candidates gathered from public recap articles.

    These are evaluated and intentionally NOT imported: they lack multi-source
    consensus and are transcribed from live-test discussions.
    """
    return [
        {
            "provenance": "transcribed_live_test",
            "exam_type": "SAT",
            "subject": "Reading",
            "topic": "Vocabulary",
            "difficulty": "Medium",
            "skill_category": "Craft and Structure",
            "question_text": (
                "Summer squash also ______ its wild ancestor. "
                "Which choice completes the text with the most logical and precise word?"
            ),
            "passage": (
                "Domesticated amaranth is physically different from its wild ancestor; "
                "its physical structure is no longer identical to the structure of the wild plant."
            ),
            "options": ["reacts to", "varies from", "helps with", "argues with"],
            "answer": "varies from",
            "explanation": (
                "Tutor recap from September 2025 International SAT Reddit threads: "
                "'varies from' matches 'is no longer identical to'."
            ),
            "strategy_tip": "Match the blank to a clue phrase in the passage.",
            "estimated_time": 70,
            "source": FORUM_SOURCE,
            "consensus_sources": 1,
        },
        {
            "provenance": "reddit_memory",
            "exam_type": "SAT",
            "subject": "Reading",
            "topic": "Vocabulary",
            "difficulty": "Medium",
            "skill_category": "Craft and Structure",
            "question_text": "Fitness trackers tend to ______ batteries that cannot be easily replaced.",
            "options": ["discover", "prepare", "imagine", "contain"],
            "answer": "contain",
            "explanation": "June 2025 International SAT forum recap suggested 'contain'.",
            "strategy_tip": "Use context clues.",
            "estimated_time": 65,
            "source": FORUM_SOURCE,
            "consensus_sources": 1,
        },
    ]


def collect_verified_forum_questions(
    existing_rows: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], ForumVerificationReport]:
    """
    Review forum-derived candidates and return only verified rows.

    Current public forum landscape yields zero importable rows under strict rules.
    """
    report = ForumVerificationReport()
    existing_fingerprints = {
        question_fingerprint(row) for row in (existing_rows or [])
    }

    candidates = _forum_review_candidates()
    report.candidates_reviewed = len(candidates)
    accepted_rows: list[dict[str, Any]] = []

    for candidate in candidates:
        consensus = int(candidate.pop("consensus_sources", 1))
        ok, reason = verify_forum_candidate(
            candidate,
            existing_fingerprints=existing_fingerprints,
            consensus_sources=consensus,
        )
        if ok:
            for exam_type in ALL_EXAM_TYPES:
                row = {**candidate, "exam_type": exam_type}
                if is_valid_question_row(row):
                    accepted_rows.append(row)
            report.accepted += 1
        else:
            report.reject(reason)

    accepted_rows, dupes = dedupe_rows(accepted_rows)
    if dupes:
        report.rejected += dupes
        report.rejection_reasons["duplicate_within_forum_batch"] = dupes

    report.notes = [
        assessment["name"] + ": " + assessment["verdict"] + " — " + assessment["reason"]
        for assessment in FORUM_SOURCE_ASSESSMENTS
    ]
    return accepted_rows, report
