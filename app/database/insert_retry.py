"""Resilient Supabase batch inserts for large uploads over flaky HTTP connections."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx

_TRANSIENT_TYPES = (
    httpx.RemoteProtocolError,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.TimeoutException,
    ConnectionError,
    ConnectionResetError,
    BrokenPipeError,
)

_TRANSIENT_MARKERS = (
    "server disconnected",
    "connection reset",
    "connection aborted",
    "timed out",
    "timeout",
    "eof occurred",
    "forcibly closed",
)


def is_transient_db_error(exc: BaseException) -> bool:
    if isinstance(exc, _TRANSIENT_TYPES):
        return True
    cause = exc.__cause__
    if isinstance(cause, _TRANSIENT_TYPES):
        return True
    message = str(exc).lower()
    return any(marker in message for marker in _TRANSIENT_MARKERS)


def _insert_with_split_retry(
    insert_fn: Callable[[list[dict[str, Any]]], None],
    batch: list[dict[str, Any]],
    *,
    depth: int = 0,
    max_depth: int = 8,
) -> None:
    if not batch:
        return
    try:
        insert_fn(batch)
    except Exception as exc:
        if not is_transient_db_error(exc) or len(batch) <= 1 or depth >= max_depth:
            raise
        midpoint = len(batch) // 2
        time.sleep(0.5 * (depth + 1))
        _insert_with_split_retry(insert_fn, batch[:midpoint], depth=depth + 1, max_depth=max_depth)
        _insert_with_split_retry(insert_fn, batch[midpoint:], depth=depth + 1, max_depth=max_depth)


def insert_batches_resilient(
    *,
    rows: list[dict[str, Any]],
    insert_batch: Callable[[list[dict[str, Any]]], None],
    batch_size: int = 25,
    progress_callback: Callable[[int, int, str], None] | None = None,
    progress_label: str = "Inserted",
    pause_between_batches_sec: float = 0.15,
) -> tuple[int, int]:
    """Insert rows in batches; split and retry transient failures. Returns (inserted, total)."""
    total = len(rows)
    if total == 0:
        return 0, 0

    total_batches = (total + batch_size - 1) // batch_size
    inserted = 0

    for batch_index, start in enumerate(range(0, total, batch_size)):
        batch = rows[start : start + batch_size]
        _insert_with_split_retry(insert_batch, batch)
        inserted = min(start + len(batch), total)
        if progress_callback:
            progress_callback(
                batch_index + 1,
                total_batches,
                f"{progress_label} {inserted}/{total} questions",
            )
        if pause_between_batches_sec and batch_index < total_batches - 1:
            time.sleep(pause_between_batches_sec)

    return inserted, total
