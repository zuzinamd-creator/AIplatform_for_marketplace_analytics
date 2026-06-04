from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.core.queue.etl_retry_policy import (
    EtlRetryableError,
    RetryReason,
    classify_retry_reason,
    compute_etl_retry_eligible_at,
)
def test_classify_lock_timeout() -> None:
    assert (
        classify_retry_reason("canceling statement due to lock timeout")
        == RetryReason.LOCK_TIMEOUT
    )
    assert (
        classify_retry_reason(
            "x",
            EtlRetryableError("y", retry_reason=RetryReason.INVENTORY_REBUILD_BUSY),
        )
        == RetryReason.INVENTORY_REBUILD_BUSY
    )


def test_exponential_backoff_increases_with_attempts() -> None:
    t1 = compute_etl_retry_eligible_at(1)
    t2 = compute_etl_retry_eligible_at(2)
    assert t2 > t1
    assert (t1 - datetime.now(UTC)).total_seconds() >= 25
    assert (t2 - t1).total_seconds() >= 25
