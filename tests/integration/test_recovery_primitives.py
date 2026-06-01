"""Integration tests for explicit tenant recovery helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.core.security_context import TenantSession
from app.models.inventory.staging import WarehouseStockSnapshotStaging
from app.models.job import EtlJob, JobStatus
from app.models.semantics.governance import RebuildOrchestrationStatus, SnapshotRebuildRequirement
from app.models.user import User
from app.operations.rebuild_orchestration import RebuildOrchestrationService
from app.operations.recovery import TenantRecoveryService
from app.services.semantics_invalidation_service import SemanticsInvalidationService
from sqlalchemy import select
from tests.integration.queue_helpers import (
    enqueue_job,
    make_job_visibility_stale,
    seed_user_and_report,
)


@pytest.mark.integration
async def test_reset_stale_running_rebuilds(session_factory) -> None:
    user_id = uuid4()
    async with session_factory() as session:
        async with session.begin():
            session.add(
                User(
                    id=user_id,
                    email=f"recovery-{user_id}@example.com",
                    hashed_password="x",
                    is_active=True,
                )
            )
        async with TenantSession.transaction(session, user_id):
            await SemanticsInvalidationService(session, user_id).request_rebuild(
                semantics_version="1.0",
                reason="stale running test",
            )
            row = (
                await session.execute(
                    select(SnapshotRebuildRequirement).where(
                        SnapshotRebuildRequirement.user_id == user_id,
                    )
                )
            ).scalar_one()
            orch = RebuildOrchestrationService(session, user_id)
            await orch.mark_running(row)
            row.started_at = datetime.now(UTC) - timedelta(hours=2)

        recovery = TenantRecoveryService(session, user_id)
        result = await recovery.reset_stale_running_rebuilds(stale_after_seconds=60)
        assert result.affected_count == 1

        async with TenantSession.transaction(session, user_id):
            refreshed = await session.get(SnapshotRebuildRequirement, row.id)
            assert refreshed is not None
            assert refreshed.orchestration_status == RebuildOrchestrationStatus.DEFERRED
            assert refreshed.next_eligible_at is not None


@pytest.mark.integration
async def test_cleanup_orphaned_staging(session_factory) -> None:
    user_id = uuid4()
    run_id = uuid4()
    async with session_factory() as session:
        async with session.begin():
            session.add(
                User(
                    id=user_id,
                    email=f"staging-{user_id}@example.com",
                    hashed_password="x",
                    is_active=True,
                )
            )
        async with TenantSession.transaction(session, user_id):
            from datetime import date
            from decimal import Decimal

            session.add(
                WarehouseStockSnapshotStaging(
                    user_id=user_id,
                    rebuild_run_id=run_id,
                    snapshot_date=date(2026, 1, 1),
                    opening_stock=0,
                    inbound_units=0,
                    sold_units=0,
                    returned_units=0,
                    lost_units=0,
                    writeoff_units=0,
                    expected_closing_stock=0,
                    actual_stock=0,
                    discrepancy_units=0,
                    discrepancy_cost=Decimal("0"),
                    discrepancy_sale_value=Decimal("0"),
                    semantics_version="1.0",
                    created_at=datetime.now(UTC) - timedelta(days=2),
                )
            )

        recovery = TenantRecoveryService(session, user_id)
        result = await recovery.cleanup_orphaned_staging(older_than_seconds=86_400)
        assert result.affected_count >= 1


@pytest.mark.integration
async def test_recover_stuck_processing_matches_global_recover(
    session_factory,
) -> None:
    fixture = await seed_user_and_report(session_factory)
    job = await enqueue_job(
        session_factory,
        fixture,
        visibility_timeout_seconds=60,
    )
    async with session_factory() as session:
        async with TenantSession.transaction(session, fixture.user_id):
            row = await session.get(EtlJob, job.id)
            assert row is not None
            row.status = JobStatus.PROCESSING
            row.claimed_at = datetime.now(UTC)
            row.attempt_count = 1

    await make_job_visibility_stale(session_factory, fixture.user_id, job.id)

    async with session_factory() as session:
        recovery = TenantRecoveryService(session, fixture.user_id)
        tenant_result = await recovery.recover_stuck_processing_jobs()
        assert tenant_result.affected_count == 1

        async with TenantSession.transaction(session, fixture.user_id):
            refreshed = await session.get(EtlJob, job.id)
            assert refreshed is not None
            assert refreshed.status == JobStatus.PENDING


@pytest.mark.integration
async def test_replay_dead_letter_with_reset(session_factory) -> None:
    fixture = await seed_user_and_report(session_factory)
    job = await enqueue_job(session_factory, fixture, max_attempts=3)
    async with session_factory() as session:
        async with TenantSession.transaction(session, fixture.user_id):
            row = await session.get(EtlJob, job.id)
            assert row is not None
            row.status = JobStatus.DEAD_LETTER
            row.attempt_count = 3
            row.last_error = "exhausted"

        recovery = TenantRecoveryService(session, fixture.user_id)
        result = await recovery.replay_dead_letter_job(
            job.id,
            reset_attempt_counter=True,
        )
        assert result.affected_count == 1

        async with TenantSession.transaction(session, fixture.user_id):
            refreshed = await session.get(EtlJob, job.id)
            assert refreshed is not None
            assert refreshed.status == JobStatus.PENDING
            assert refreshed.attempt_count == 0
