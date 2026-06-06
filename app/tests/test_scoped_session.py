from app.utils.scoped_session import scoped_key


def test_scoped_key_includes_user_namespace():
    key = scoped_key("practice_feedback")
    assert key.startswith("u:")
    assert key.endswith(":practice_feedback")
