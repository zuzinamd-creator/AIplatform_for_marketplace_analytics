from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.queue.stale import is_etl_job_stale
from app.models.job import EtlJob, JobStatus


def _job(*, claimed_at: datetime, heartbeat_at: datetime | None, timeout: int = 60) -> EtlJob:
    return EtlJob(
        user_id=__import__("uuid").uuid4(),
        report_id=__import__("uuid").uuid4(),
        status=JobStatus.PROCESSING,
        attempt_count=1,
        max_attempts=3,
        visibility_timeout_seconds=timeout,
        claimed_at=claimed_at,
        last_heartbeat_at=heartbeat_at,
        idempotency_key="k",
        report_created_at=datetime.now(UTC),
    )


def test_stale_when_heartbeat_expired() -> None:
    now = datetime.now(UTC)
    job = _job(
        claimed_at=now - timedelta(seconds=120),
        heartbeat_at=now - timedelta(seconds=90),
        timeout=60,
    )
    assert is_etl_job_stale(job, now) is True


def test_not_stale_when_heartbeat_fresh_but_claim_old() -> None:
    now = datetime.now(UTC)
    job = _job(
        claimed_at=now - timedelta(seconds=3600),
        heartbeat_at=now - timedelta(seconds=10),
        timeout=60,
    )
    assert is_etl_job_stale(job, now) is False


def test_stale_fallback_to_claim_when_no_heartbeat() -> None:
    now = datetime.now(UTC)
    job = _job(claimed_at=now - timedelta(seconds=120), heartbeat_at=None, timeout=60)
    assert is_etl_job_stale(job, now) is True
