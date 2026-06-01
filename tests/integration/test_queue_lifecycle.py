"""Production queue lifecycle: enqueue, claim, ack, retry, visibility recovery, concurrency."""

from __future__ import annotations

import pytest
from app.core.queue import get_queue_backend
from app.core.security_context import TenantSession
from app.models.job import EtlJob, JobStatus
from sqlalchemy import func, select
from tests.integration.queue_helpers import (
    QueueFixture,
    claim_next,
    concurrent_claim,
    count_jobs_with_status,
    enqueue_job,
    load_job,
    make_job_visibility_stale,
    recover_stale,
    refresh_job_heartbeat,
    seed_user_and_report,
    wait_for_job_status,
)


@pytest.mark.integration
async def test_enqueue_idempotent_for_active_jobs(session_factory) -> None:
    fixture = await seed_user_and_report(session_factory)
    first = await enqueue_job(session_factory, fixture)
    second = await enqueue_job(session_factory, fixture)

    assert first.id == second.id
    assert first.status == JobStatus.PENDING

    async with session_factory() as session:
        async with TenantSession.transaction(session, fixture.user_id):
            total = (
                await session.execute(
                    select(func.count())
                    .select_from(EtlJob)
                    .where(
                        EtlJob.user_id == fixture.user_id,
                        EtlJob.idempotency_key == fixture.idempotency_key,
                    )
                )
            ).scalar_one()
    assert total == 1


@pytest.mark.integration
async def test_fail_retry_deterministic_attempt_progression(session_factory) -> None:
    fixture = await seed_user_and_report(session_factory)
    job = await enqueue_job(session_factory, fixture, max_attempts=3)
    max_attempts = 3

    for attempt in (1, 2, 3):
        claimed = await claim_next(session_factory)
        assert claimed is not None
        assert claimed.job_id == job.id
        assert claimed.attempt_count == attempt

        async with session_factory() as session:
            if attempt < max_attempts:
                async with TenantSession.transaction(session, fixture.user_id):
                    await get_queue_backend(session).fail(
                        str(job.id),
                        error_message=f"transient-{attempt}",
                        attempt_count=claimed.attempt_count,
                        max_attempts=max_attempts,
                    )
                refreshed = await wait_for_job_status(
                    session_factory,
                    fixture.user_id,
                    job.id,
                    JobStatus.PENDING,
                )
                assert refreshed.attempt_count == attempt
            else:
                async with TenantSession.transaction(session, fixture.user_id):
                    await get_queue_backend(session).fail(
                        str(job.id),
                        error_message="terminal",
                        attempt_count=claimed.attempt_count,
                        max_attempts=max_attempts,
                    )
                refreshed = await wait_for_job_status(
                    session_factory,
                    fixture.user_id,
                    job.id,
                    JobStatus.DEAD_LETTER,
                )
                assert refreshed.attempt_count == attempt

    processing_left = await count_jobs_with_status(
        session_factory, fixture.user_id, JobStatus.PROCESSING
    )
    assert processing_left == 0


@pytest.mark.integration
async def test_visibility_timeout_recovery_without_wall_clock_sleep(session_factory) -> None:
    fixture = await seed_user_and_report(session_factory)
    job = await enqueue_job(
        session_factory,
        fixture,
        max_attempts=3,
        visibility_timeout_seconds=60,
    )

    claimed = await claim_next(session_factory)
    assert claimed is not None
    assert claimed.attempt_count == 1

    await make_job_visibility_stale(session_factory, fixture.user_id, job.id)
    recovered = await recover_stale(session_factory)
    assert len(recovered) == 1
    assert recovered[0].job_id == job.id
    assert recovered[0].new_status == JobStatus.PENDING.value

    refreshed = await load_job(session_factory, fixture.user_id, job.id)
    assert refreshed.status == JobStatus.PENDING
    assert refreshed.claimed_at is None
    assert "Visibility timeout" in (refreshed.last_error or "")

    reclaimed = await claim_next(session_factory)
    assert reclaimed is not None
    assert reclaimed.attempt_count == 2


@pytest.mark.integration
async def test_visibility_timeout_dead_letters_when_attempts_exhausted(session_factory) -> None:
    fixture = await seed_user_and_report(session_factory)
    job = await enqueue_job(
        session_factory,
        fixture,
        max_attempts=2,
        visibility_timeout_seconds=30,
    )

    first = await claim_next(session_factory)
    assert first is not None
    await make_job_visibility_stale(session_factory, fixture.user_id, job.id)
    await recover_stale(session_factory)

    second = await claim_next(session_factory)
    assert second is not None
    assert second.attempt_count == 2

    await make_job_visibility_stale(session_factory, fixture.user_id, job.id)
    recovered = await recover_stale(session_factory)
    assert len(recovered) == 1
    assert recovered[0].new_status == JobStatus.DEAD_LETTER.value

    final = await load_job(session_factory, fixture.user_id, job.id)
    assert final.status == JobStatus.DEAD_LETTER
    assert "Max attempts exceeded" in (final.last_error or "")
    assert await count_jobs_with_status(
        session_factory, fixture.user_id, JobStatus.PROCESSING
    ) == 0


@pytest.mark.integration
async def test_recover_stale_skips_jobs_within_visibility_window(session_factory) -> None:
    fixture = await seed_user_and_report(session_factory)
    job = await enqueue_job(
        session_factory,
        fixture,
        visibility_timeout_seconds=3600,
    )
    claimed = await claim_next(session_factory)
    assert claimed is not None

    await refresh_job_heartbeat(session_factory, fixture.user_id, job.id)
    recovered = await recover_stale(session_factory)
    assert recovered == []

    still_processing = await load_job(session_factory, fixture.user_id, job.id)
    assert still_processing.status == JobStatus.PROCESSING


@pytest.mark.integration
async def test_concurrent_claim_single_job_no_duplicate_processing(session_factory) -> None:
    fixture = await seed_user_and_report(session_factory)
    job = await enqueue_job(session_factory, fixture)

    results = await concurrent_claim(session_factory, 8)

    claimed = [r for r in results if r is not None]
    assert len(claimed) == 1
    assert claimed[0].job_id == job.id

    second_wave = await concurrent_claim(session_factory, 4)
    assert all(r is None for r in second_wave)

    row = await load_job(session_factory, fixture.user_id, job.id)
    assert row.status == JobStatus.PROCESSING
    assert row.attempt_count == 1


@pytest.mark.integration
async def test_concurrent_claim_distinct_jobs_no_overlap(session_factory) -> None:
    fixtures: list[QueueFixture] = []
    job_ids = []
    for _ in range(3):
        fixture = await seed_user_and_report(session_factory)
        job = await enqueue_job(session_factory, fixture)
        fixtures.append(fixture)
        job_ids.append(job.id)

    # Some environments may not schedule enough true parallel DB connections in a single wave.
    # We still require the queue to eventually claim all distinct jobs without overlap.
    claimed_all = []
    for _ in range(5):
        results = await concurrent_claim(session_factory, 6)
        claimed_all.extend([r for r in results if r is not None])
        if len({r.job_id for r in claimed_all}) >= 3:
            break

    claimed_ids = {r.job_id for r in claimed_all}
    assert claimed_ids == set(job_ids)

    for fixture in fixtures:
        processing = await count_jobs_with_status(
            session_factory, fixture.user_id, JobStatus.PROCESSING
        )
        assert processing == 1


@pytest.mark.integration
async def test_ack_leaves_no_orphan_processing_jobs(session_factory) -> None:
    fixtures: list[QueueFixture] = []
    for _ in range(2):
        fixture = await seed_user_and_report(session_factory)
        await enqueue_job(session_factory, fixture)
        fixtures.append(fixture)

    claimed_all = []
    for _ in range(5):
        claimed = await concurrent_claim(session_factory, 2)
        claimed_all.extend([r for r in claimed if r is not None])
        if len({r.job_id for r in claimed_all}) >= 2:
            break
    jobs = []
    seen = set()
    for r in claimed_all:
        if r.job_id not in seen:
            jobs.append(r)
            seen.add(r.job_id)
    assert len(jobs) == 2

    for job in jobs:
        async with session_factory() as session:
            async with TenantSession.transaction(session, job.user_id):
                await get_queue_backend(session).ack(str(job.job_id))

    for fixture in fixtures:
        assert (
            await count_jobs_with_status(
                session_factory, fixture.user_id, JobStatus.PROCESSING
            )
            == 0
        )
        assert (
            await count_jobs_with_status(
                session_factory, fixture.user_id, JobStatus.COMPLETED
            )
            == 1
        )
        assert (
            await count_jobs_with_status(
                session_factory, fixture.user_id, JobStatus.PENDING
            )
            == 0
        )


@pytest.mark.integration
async def test_worker_recover_then_claim_lifecycle(session_factory) -> None:
    """Mirrors worker loop: recover_stale → claim → ack without orphan PROCESSING rows."""
    fixture = await seed_user_and_report(session_factory)
    job = await enqueue_job(
        session_factory,
        fixture,
        max_attempts=2,
        visibility_timeout_seconds=45,
    )

    claimed = await claim_next(session_factory)
    assert claimed is not None
    await make_job_visibility_stale(session_factory, fixture.user_id, job.id)

    await recover_stale(session_factory)
    reclaimed = await claim_next(session_factory)
    assert reclaimed is not None
    assert reclaimed.attempt_count == 2

    async with session_factory() as session:
        async with TenantSession.transaction(session, fixture.user_id):
            await get_queue_backend(session).ack(str(job.id))

    final = await load_job(session_factory, fixture.user_id, job.id)
    assert final.status == JobStatus.COMPLETED
    assert final.claimed_at is None
    assert await count_jobs_with_status(
        session_factory, fixture.user_id, JobStatus.PROCESSING
    ) == 0
