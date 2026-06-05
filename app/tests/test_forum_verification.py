from app.database.official_loaders.forum_verification import (
    collect_verified_forum_questions,
    verify_forum_candidate,
)


def test_forum_candidates_rejected_by_default():
    rows, report = collect_verified_forum_questions()
    assert rows == []
    assert report.accepted == 0
    assert report.candidates_reviewed >= 2


def test_single_source_forum_candidate_rejected():
    candidate = {
        "provenance": "reddit_memory",
        "exam_type": "SAT",
        "subject": "Reading",
        "topic": "Vocabulary",
        "difficulty": "Easy",
        "skill_category": "Craft and Structure",
        "question_text": "The speaker was candid, so the audience trusted her remarks.",
        "options": ["honest", "silent", "angry", "confused"],
        "answer": "honest",
        "explanation": "Short.",
        "strategy_tip": "Use context.",
        "estimated_time": 60,
        "source": "forum_verified",
    }
    ok, reason = verify_forum_candidate(candidate, consensus_sources=1)
    assert not ok
    assert reason in {"insufficient_consensus_sources", "explanation_too_short_for_verification", "unauthorized_or_unverifiable_provenance"}
