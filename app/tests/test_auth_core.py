from unittest.mock import MagicMock, patch

from app.authentication.auth_core import sign_in


def test_sign_in_requires_email_and_password():
    assert sign_in("", "x")["ok"] is False
    assert sign_in("a@b.com", "")["ok"] is False


@patch("app.authentication.auth_core.get_public_client")
def test_sign_in_success(mock_get_client):
    mock_user = MagicMock()
    mock_user.id = "uuid-1"
    mock_user.email = "student@test.local"

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.user = mock_user
    mock_client.auth.sign_in_with_password.return_value = mock_response
    mock_get_client.return_value = mock_client

    result = sign_in("student@test.local", "TestPassword123!")
    assert result["ok"] is True
    assert result["user_id"] == "uuid-1"
    mock_client.auth.sign_in_with_password.assert_called_once_with(
        {"email": "student@test.local", "password": "TestPassword123!"}
    )


@patch("app.authentication.auth_core.get_public_client")
def test_sign_in_invalid_credentials(mock_get_client):
    mock_client = MagicMock()
    mock_client.auth.sign_in_with_password.side_effect = Exception("Invalid login credentials")
    mock_get_client.return_value = mock_client

    result = sign_in("student@test.local", "wrong")
    assert result["ok"] is False
    assert "hint" in result
