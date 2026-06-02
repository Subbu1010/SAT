from app.database.seed_data import DEFAULT_TEST_PASSWORD, SAMPLE_QUESTIONS, TEST_USERS


def test_test_users_have_unique_emails():
    emails = [u["email"] for u in TEST_USERS]
    assert len(emails) == len(set(emails))


def test_test_users_roles():
    roles = {u["role"] for u in TEST_USERS}
    assert roles == {"admin", "teacher", "student"}


def test_default_password_length():
    assert len(DEFAULT_TEST_PASSWORD) >= 12


def test_sample_questions_have_required_fields():
    required = {"exam_type", "subject", "topic", "difficulty", "question_text", "options", "answer"}
    for q in SAMPLE_QUESTIONS:
        assert required.issubset(q.keys())
        assert len(q["options"]) >= 2
