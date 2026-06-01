from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.core.queue import EnqueuePayload, get_queue_backend
from app.core.security_context import TenantSession
from app.models.job import EtlJob as JobModel
from app.models.job import JobStatus
from app.models.report import Marketplace, Report, ReportType
from app.models.user import User
from sqlalchemy import select


@pytest.mark.integration
async def test_queue_enqueue_claim_ack(session_factory) -> None:
    user = User(
        id=uuid4(),
        email=f"{uuid4()}@example.com",
        hashed_password="x",
        is_active=True,
    )
    report = Report(
        id=uuid4(),
        user_id=user.id,
        marketplace=Marketplace.WILDBERRIES,
        report_type=ReportType.SALES,
        original_filename="demo.csv",
        file_path="reports/demo.csv",
        file_checksum=f"checksum-{uuid4()}",
    )
    async with session_factory() as session:
        async with session.begin():
            session.add(user)
            await session.flush()

    async with session_factory() as session:
        async with TenantSession.transaction(session, user.id):
            session.add(report)
            await session.flush()

    payload = EnqueuePayload(
        user_id=user.id,
        report_id=report.id,
        idempotency_key=report.file_checksum or "integration-test-checksum",
        file_path="reports/demo.csv",
        marketplace="wildberries",
        report_type="sales",
        original_filename="demo.csv",
        report_created_at=datetime.now(UTC),
    )

    async with session_factory() as session:
        async with TenantSession.transaction(session, user.id):
            job = await get_queue_backend(session).enqueue(payload)
    assert job.status == JobStatus.PENDING

    async with session_factory() as session:
        claimed = await get_queue_backend(session).claim()
    assert claimed is not None
    assert claimed.report_id == report.id

    async with session_factory() as session:
        async with TenantSession.transaction(session, user.id):
            await get_queue_backend(session).ack(str(claimed.job_id))

    async with session_factory() as session:
        async with TenantSession.transaction(session, user.id):
            result = await session.execute(select(JobModel).where(JobModel.id == claimed.job_id))
            refreshed = result.scalar_one()
    assert refreshed.status == JobStatus.COMPLETED
