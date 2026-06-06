from app.utils.user_session import _is_legacy_user_session_key


def test_legacy_user_session_key_detection():
    assert _is_legacy_user_session_key("practice_feedback")
    assert _is_legacy_user_session_key("practice_opts_abc")
    assert _is_legacy_user_session_key("exam_answers")
    assert _is_legacy_user_session_key("tutor_messages")
    assert _is_legacy_user_session_key("topics_Math")
    assert _is_legacy_user_session_key("adaptive_difficulty")
    assert not _is_legacy_user_session_key("auth_user")
    assert not _is_legacy_user_session_key("_bootstrap_done")
    assert not _is_legacy_user_session_key("active_user_id")
    assert not _is_legacy_user_session_key("u:abc:practice_feedback")
