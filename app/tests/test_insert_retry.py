from unittest.mock import MagicMock

import httpx
import pytest

from app.database.insert_retry import insert_batches_resilient, is_transient_db_error


def test_is_transient_db_error_detects_remote_protocol_error():
    assert is_transient_db_error(httpx.RemoteProtocolError("Server disconnected"))


def test_is_transient_db_error_rejects_validation_error():
    assert not is_transient_db_error(ValueError("bad row"))


def test_insert_batches_resilient_splits_on_transient_failure():
    calls: list[int] = []

    def insert_batch(batch: list[dict]) -> None:
        calls.append(len(batch))
        if len(batch) > 1:
            raise httpx.RemoteProtocolError("Server disconnected")

    inserted, total = insert_batches_resilient(
        rows=[{"question_id": f"q{i}"} for i in range(4)],
        insert_batch=insert_batch,
        batch_size=4,
        pause_between_batches_sec=0,
    )

    assert inserted == 4
    assert total == 4
    assert calls[0] == 4
    assert 1 in calls
    assert all(size >= 1 for size in calls)


def test_insert_batches_resilient_raises_non_transient_errors():
    insert_batch = MagicMock(side_effect=ValueError("duplicate key"))

    with pytest.raises(ValueError, match="duplicate key"):
        insert_batches_resilient(
            rows=[{"question_id": "q1"}],
            insert_batch=insert_batch,
            pause_between_batches_sec=0,
        )
