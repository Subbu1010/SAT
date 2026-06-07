from unittest.mock import MagicMock, patch

from app.services import login_history_service as service


@patch("app.services.login_history_service.get_supabase_admin_client")
def test_log_login_event_retries_without_location_when_column_missing(mock_client):
    service._location_column_available = True
    admin = MagicMock()
    mock_client.return_value = admin
    admin.table.return_value.insert.return_value.execute.side_effect = [
        Exception("Could not find the 'location' column"),
        None,
    ]

    service.log_login_event(
        email="user@test.local",
        status="success",
        ip_address="localhost",
        location="Local / unknown",
    )

    assert admin.table.return_value.insert.return_value.execute.call_count == 2
    second_row = admin.table.return_value.insert.call_args_list[1].args[0]
    assert "location" not in second_row
    assert second_row["ip_address"] == "localhost"
