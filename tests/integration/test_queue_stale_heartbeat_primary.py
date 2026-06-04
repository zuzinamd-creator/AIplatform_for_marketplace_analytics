"""Heartbeat-primary stale recovery — long persist must not requeue active jobs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.core.queue import get_queue_backend
from app.core.security_context import TenantSession
from app.models.job import EtlJob, JobStatus
from tests.integration.queue_helpers import (
    QueueFixture,
    claim_next,
    enqueue_job,
    load_job,
    recover_stale,
    seed_user_and_report,
)


@pytest.mark.integration
async def test_recover_stale_ignores_stale_claim_when_heartbeat_fresh(session_factory) -> None:
    fixture = await seed_user_and_report(session_factory)
    job = await enqueue_job(
        session_factory,
        fixture,
        visibility_timeout_seconds=60,
    )
    claimed = await claim_next(session_factory)
    assert claimed is not None

    async with session_factory() as session:
        async with TenantSession.transaction(session, fixture.user_id):
            row = await session.get(EtlJob, job.id)
            assert row is not None
            row.claimed_at = datetime.now(UTC) - timedelta(seconds=3600)
            row.last_heartbeat_at = datetime.now(UTC)

    recovered = await recover_stale(session_factory)
    assert recovered == []

    still = await load_job(session_factory, fixture.user_id, job.id)
    assert still.status == JobStatus.PROCESSING
