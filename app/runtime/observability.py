"""Queue and rebuild orchestration observability."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security_context import DispatchSession, TenantSession
from app.core.tenant_context import set_current_user_context, set_queue_role_context
from app.models.job import EtlJob, JobStatus
from app.models.semantics.governance import RebuildOrchestrationStatus, SnapshotRebuildRequirement
from app.operations.safety_guards import ProductionSafetyGuards
from app.runtime.metrics import emit_runtime_metric


@asynccontextmanager
async def _tenant_metrics_context(
    db: AsyncSession, user_id: UUID
) -> AsyncGenerator[None, None]:
    """RLS context for tenant metrics; reuses open transaction when present."""
    if db.in_transaction():
        await set_queue_role_context(db, False)
        await set_current_user_context(db, user_id)
        yield
    else:
        async with TenantSession.transaction(db, user_id):
            yield


@dataclass(frozen=True)
class QueueObservabilitySnapshot:
    pending_count: int
    processing_count: int
    dead_letter_count: int
    oldest_pending_lag_seconds: int | None


@dataclass(frozen=True)
class RebuildQueueObservabilitySnapshot:
    pending_dispatch: int
    deferred: int
    running: int
    failed: int


async def collect_global_queue_metrics(db: AsyncSession) -> QueueObservabilitySnapshot:
    async with DispatchSession.transaction(db):
        pending = (
            await db.execute(
                select(func.count()).select_from(EtlJob).where(EtlJob.status == JobStatus.PENDING)
            )
        ).scalar_one()
        processing = (
            await db.execute(
                select(func.count())
                .select_from(EtlJob)
                .where(EtlJob.status == JobStatus.PROCESSING)
            )
        ).scalar_one()
        dead_letter = (
            await db.execute(
                select(func.count())
                .select_from(EtlJob)
                .where(EtlJob.status == JobStatus.DEAD_LETTER)
            )
        ).scalar_one()
        oldest = (
            await db.execute(
                select(func.min(EtlJob.created_at)).where(EtlJob.status == JobStatus.PENDING)
            )
        ).scalar_one()

    lag: int | None = None
    if oldest is not None:
        lag = int((datetime.now(UTC) - oldest).total_seconds())

    snap = QueueObservabilitySnapshot(
        pending_count=int(pending),
        processing_count=int(processing),
        dead_letter_count=int(dead_letter),
        oldest_pending_lag_seconds=lag,
    )
    emit_runtime_metric(
        "runtime_queue_metrics",
        pending_count=snap.pending_count,
        processing_count=snap.processing_count,
        dead_letter_count=snap.dead_letter_count,
        queue_lag_seconds=lag,
    )
    if lag is not None and lag > settings.ops_queue_lag_warn_seconds:
        emit_runtime_metric(
            "runtime_queue_lag_high",
            queue_lag_seconds=lag,
            threshold_seconds=settings.ops_queue_lag_warn_seconds,
        )
    return snap


async def collect_rebuild_queue_metrics(db: AsyncSession) -> RebuildQueueObservabilitySnapshot:
    async with DispatchSession.transaction(db):
        pending_dispatch = (
            await db.execute(
                select(func.count())
                .select_from(SnapshotRebuildRequirement)
                .where(
                    SnapshotRebuildRequirement.requires_rebuild.is_(True),
                    SnapshotRebuildRequirement.orchestration_status.in_(
                        (
                            RebuildOrchestrationStatus.PENDING,
                            RebuildOrchestrationStatus.QUEUED,
                        )
                    ),
                )
            )
        ).scalar_one()
        deferred = (
            await db.execute(
                select(func.count())
                .select_from(SnapshotRebuildRequirement)
                .where(
                    SnapshotRebuildRequirement.orchestration_status
                    == RebuildOrchestrationStatus.DEFERRED,
                )
            )
        ).scalar_one()
        running = (
            await db.execute(
                select(func.count())
                .select_from(SnapshotRebuildRequirement)
                .where(
                    SnapshotRebuildRequirement.orchestration_status
                    == RebuildOrchestrationStatus.RUNNING,
                )
            )
        ).scalar_one()
        failed = (
            await db.execute(
                select(func.count())
                .select_from(SnapshotRebuildRequirement)
                .where(
                    SnapshotRebuildRequirement.orchestration_status
                    == RebuildOrchestrationStatus.FAILED,
                )
            )
        ).scalar_one()

    snap = RebuildQueueObservabilitySnapshot(
        pending_dispatch=int(pending_dispatch),
        deferred=int(deferred),
        running=int(running),
        failed=int(failed),
    )
    emit_runtime_metric(
        "runtime_rebuild_queue_metrics",
        rebuild_pending_dispatch=snap.pending_dispatch,
        rebuild_deferred=snap.deferred,
        rebuild_running=snap.running,
        rebuild_failed=snap.failed,
    )
    if snap.running > 0:
        emit_runtime_metric("runtime_rebuild_running_count", rebuild_running=snap.running)
    return snap


async def collect_tenant_queue_metrics(
    db: AsyncSession,
    user_id: UUID,
) -> QueueObservabilitySnapshot:
    async with _tenant_metrics_context(db, user_id):
        pending = (
            await db.execute(
                select(func.count())
                .select_from(EtlJob)
                .where(EtlJob.user_id == user_id, EtlJob.status == JobStatus.PENDING)
            )
        ).scalar_one()
        processing = (
            await db.execute(
                select(func.count())
                .select_from(EtlJob)
                .where(EtlJob.user_id == user_id, EtlJob.status == JobStatus.PROCESSING)
            )
        ).scalar_one()
        dead_letter = (
            await db.execute(
                select(func.count())
                .select_from(EtlJob)
                .where(EtlJob.user_id == user_id, EtlJob.status == JobStatus.DEAD_LETTER)
            )
        ).scalar_one()
        oldest = (
            await db.execute(
                select(func.min(EtlJob.created_at)).where(
                    EtlJob.user_id == user_id,
                    EtlJob.status == JobStatus.PENDING,
                )
            )
        ).scalar_one()

    lag: int | None = None
    if oldest is not None:
        lag = int((datetime.now(UTC) - oldest).total_seconds())

    return QueueObservabilitySnapshot(
        pending_count=int(pending),
        processing_count=int(processing),
        dead_letter_count=int(dead_letter),
        oldest_pending_lag_seconds=lag,
    )


async def collect_tenant_rebuild_metrics(
    db: AsyncSession,
    user_id: UUID,
) -> RebuildQueueObservabilitySnapshot:
    async with _tenant_metrics_context(db, user_id):
        pending_dispatch = (
            await db.execute(
                select(func.count())
                .select_from(SnapshotRebuildRequirement)
                .where(
                    SnapshotRebuildRequirement.user_id == user_id,
                    SnapshotRebuildRequirement.requires_rebuild.is_(True),
                    SnapshotRebuildRequirement.orchestration_status.in_(
                        (
                            RebuildOrchestrationStatus.PENDING,
                            RebuildOrchestrationStatus.QUEUED,
                        )
                    ),
                )
            )
        ).scalar_one()
        deferred = (
            await db.execute(
                select(func.count())
                .select_from(SnapshotRebuildRequirement)
                .where(
                    SnapshotRebuildRequirement.user_id == user_id,
                    SnapshotRebuildRequirement.orchestration_status
                    == RebuildOrchestrationStatus.DEFERRED,
                )
            )
        ).scalar_one()
        running = (
            await db.execute(
                select(func.count())
                .select_from(SnapshotRebuildRequirement)
                .where(
                    SnapshotRebuildRequirement.user_id == user_id,
                    SnapshotRebuildRequirement.orchestration_status
                    == RebuildOrchestrationStatus.RUNNING,
                )
            )
        ).scalar_one()
        failed = (
            await db.execute(
                select(func.count())
                .select_from(SnapshotRebuildRequirement)
                .where(
                    SnapshotRebuildRequirement.user_id == user_id,
                    SnapshotRebuildRequirement.orchestration_status
                    == RebuildOrchestrationStatus.FAILED,
                )
            )
        ).scalar_one()

    return RebuildQueueObservabilitySnapshot(
        pending_dispatch=int(pending_dispatch),
        deferred=int(deferred),
        running=int(running),
        failed=int(failed),
    )


async def collect_tenant_health_metrics(db: AsyncSession, user_id: UUID) -> None:
    guards = ProductionSafetyGuards(db, user_id)
    async with TenantSession.transaction(db, user_id):
        for result in await guards.evaluate_tenant_health():
            if result.triggered:
                emit_runtime_metric(
                    "runtime_tenant_health_warning",
                    user_id=str(user_id),
                    check=result.check,
                    value=result.value,
                    threshold=result.threshold,
                )
