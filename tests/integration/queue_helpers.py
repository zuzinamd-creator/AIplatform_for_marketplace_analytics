"""Helpers for deterministic PostgreSQL queue integration tests."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.core.queue import EnqueuePayload, get_queue_backend
from app.core.queue.types import ClaimedJobRecord
from app.core.security_context import TenantSession
from app.models.job import EtlJob, JobStatus
from app.models.report import Marketplace, Report, ReportType
from app.models.user import User
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker


@dataclass(frozen=True)
class QueueFixture:
    user_id: UUID
    report_id: UUID
    idempotency_key: str


async def seed_user_and_report(
    session_factory: async_sessionmaker,
    *,
    idempotency_key: str | None = None,
    file_path: str = "reports/queue-lifecycle.csv",
) -> QueueFixture:
    user = User(
        id=uuid4(),
        email=f"{uuid4()}@example.com",
        hashed_password="x",
        is_active=True,
    )
    key = idempotency_key or f"checksum-{uuid4()}"
    report = Report(
        id=uuid4(),
        user_id=user.id,
        marketplace=Marketplace.WILDBERRIES,
        report_type=ReportType.SALES,
        original_filename="queue.csv",
        file_path=file_path,
        file_checksum=key,
    )
    async with session_factory() as session:
        async with session.begin():
            session.add(user)
            await session.flush()

    async with session_factory() as session:
        async with TenantSession.transaction(session, user.id):
            session.add(report)
            await session.flush()

    return QueueFixture(user_id=user.id, report_id=report.id, idempotency_key=key)


def enqueue_payload(
    fixture: QueueFixture,
    *,
    max_attempts: int = 3,
    visibility_timeout_seconds: int = 1800,
    file_path: str = "reports/queue-lifecycle.csv",
) -> EnqueuePayload:
    now = datetime.now(UTC)
    return EnqueuePayload(
        user_id=fixture.user_id,
        report_id=fixture.report_id,
        idempotency_key=fixture.idempotency_key,
        file_path=file_path,
        marketplace="wildberries",
        report_type="sales",
        original_filename="queue.csv",
        report_created_at=now,
        max_attempts=max_attempts,
        visibility_timeout_seconds=visibility_timeout_seconds,
    )


async def enqueue_job(
    session_factory: async_sessionmaker,
    fixture: QueueFixture,
    **payload_kwargs: object,
) -> EtlJob:
    payload = enqueue_payload(fixture, **payload_kwargs)  # type: ignore[arg-type]
    async with session_factory() as session:
        async with TenantSession.transaction(session, fixture.user_id):
            return await get_queue_backend(session).enqueue(payload)


async def claim_next(session_factory: async_sessionmaker) -> ClaimedJobRecord | None:
    async with session_factory() as session:
        return await get_queue_backend(session).claim()


async def recover_stale(session_factory: async_sessionmaker):
    async with session_factory() as session:
        return await get_queue_backend(session).recover_stale()


async def load_job(
    session_factory: async_sessionmaker,
    user_id: UUID,
    job_id: UUID,
) -> EtlJob:
    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            result = await session.execute(select(EtlJob).where(EtlJob.id == job_id))
            job = result.scalar_one()
            return job  # type: ignore[no-any-return]


async def count_jobs_with_status(
    session_factory: async_sessionmaker,
    user_id: UUID,
    status: JobStatus,
) -> int:
    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            count = (
                await session.execute(
                    select(func.count()).select_from(EtlJob).where(
                        EtlJob.user_id == user_id,
                        EtlJob.status == status,
                    )
                )
            ).scalar_one()
            return int(count)


async def make_job_visibility_stale(
    session_factory: async_sessionmaker,
    user_id: UUID,
    job_id: UUID,
    *,
    extra_seconds: int = 5,
) -> None:
    """Backdate claim/heartbeat so recover_stale() fires without wall-clock sleep."""
    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            job = await session.get(EtlJob, job_id)
            if job is None:
                raise AssertionError(f"job {job_id} not found")
            offset = job.visibility_timeout_seconds + extra_seconds
            stale_at = datetime.now(UTC) - timedelta(seconds=offset)
            job.claimed_at = stale_at
            job.last_heartbeat_at = stale_at


async def refresh_job_heartbeat(
    session_factory: async_sessionmaker,
    user_id: UUID,
    job_id: UUID,
) -> None:
    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            await get_queue_backend(session).heartbeat(str(job_id))


async def concurrent_claim(
    session_factory: async_sessionmaker,
    worker_count: int,
) -> list[ClaimedJobRecord | None]:
    """Release all claimers together (event gate, no wall-clock sleep)."""
    gate = asyncio.Event()

    async def _worker() -> ClaimedJobRecord | None:
        await gate.wait()
        return await claim_next(session_factory)

    tasks = [asyncio.create_task(_worker()) for _ in range(worker_count)]
    for _ in range(100):
        await asyncio.sleep(0)
    gate.set()
    return list(await asyncio.gather(*tasks))


async def poll_until(
    predicate,
    *,
    max_ticks: int = 500,
) -> None:
    """Yield to the event loop until predicate() is true (no wall-clock sleep)."""
    for _ in range(max_ticks):
        if await predicate():
            return
        await asyncio.sleep(0)
    raise AssertionError("poll_until timed out")


async def wait_for_job_status(
    session_factory: async_sessionmaker,
    user_id: UUID,
    job_id: UUID,
    expected: JobStatus,
) -> EtlJob:
    seen: EtlJob | None = None

    async def _ready() -> bool:
        nonlocal seen
        seen = await load_job(session_factory, user_id, job_id)
        return seen.status == expected

    await poll_until(_ready)
    assert seen is not None
    return seen
