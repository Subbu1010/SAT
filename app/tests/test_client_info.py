from unittest.mock import MagicMock, patch

from app.utils import client_info


def test_resolve_ip_location_returns_local_for_missing_ip():
    assert client_info.resolve_ip_location(None) == "Local / unknown"


def test_audit_ip_label_uses_localhost_when_ip_missing():
    assert client_info._audit_ip_label(None) == "localhost"


def test_resolve_ip_location_returns_private_label_for_lan_ip():
    assert client_info.resolve_ip_location("192.168.1.10") == "Local / private network"


@patch("app.utils.client_info.st")
@patch("app.utils.client_info.urllib.request.urlopen")
def test_resolve_ip_location_formats_public_ip(mock_urlopen, mock_st):
    mock_st.session_state = {}
    mock_response = MagicMock()
    mock_response.read.return_value = (
        b'{"city":"Austin","region":"Texas","country_name":"United States"}'
    )
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    assert client_info.resolve_ip_location("8.8.8.8") == "Austin, Texas, United States"


@patch("app.utils.client_info.get_client_ip", return_value=None)
def test_get_client_audit_info_uses_localhost_label_when_ip_missing(mock_get_ip):
    ip, location = client_info.get_client_audit_info()
    assert ip == "localhost"
    assert location == "Local / unknown"


@patch("app.utils.client_info.get_client_ip", return_value="8.8.4.4")
@patch("app.utils.client_info.resolve_ip_location", return_value="Dallas, Texas, United States")
def test_get_client_audit_info_returns_ip_and_location(mock_resolve, mock_get_ip):
    assert client_info.get_client_audit_info() == ("8.8.4.4", "Dallas, Texas, United States")
