import pytest

from app.authentication.auth_core import sign_in
from app.database.seed import seed_test_users
from app.database.seed_data import DEFAULT_TEST_PASSWORD, TEST_USERS


@pytest.mark.integration
def test_seed_and_login_all_test_users():
    ok, message = seed_test_users()
    assert ok, message

    for user in TEST_USERS:
        result = sign_in(user["email"], DEFAULT_TEST_PASSWORD)
        assert result["ok"], f"Login failed for {user['email']}: {result.get('error')}"
        assert result["user_id"]


@pytest.mark.integration
def test_login_wrong_password_fails():
    result = sign_in("student@test.local", "NotTheRightPassword!")
    assert result["ok"] is False
