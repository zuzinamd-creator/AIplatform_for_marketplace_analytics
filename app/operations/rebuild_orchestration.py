"""Rebuild queue prioritization, retry metadata, fairness, and throttling primitives."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from app.models.semantics.governance import (
    RebuildOrchestrationStatus,
    SnapshotRebuildRequirement,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class RebuildPriority:
    """Lower numeric value = higher priority."""

    SEMANTICS_INVALIDATION = 10
    DRIFT_REPAIR = 30
    OPERATOR_REQUEST = 50
    DEFAULT = 100
    BACKFILL = 200


@dataclass(frozen=True)
class RetryMetadata:
    attempt_count: int
    max_attempts: int
    next_eligible_at: datetime | None
    last_error: str | None

    @property
    def exhausted(self) -> bool:
        return self.attempt_count >= self.max_attempts


@dataclass(frozen=True)
class TenantThrottlePolicy:
    """Matches advisory-lock reality: one inventory rebuild per tenant at a time."""

    max_concurrent_rebuilds_per_tenant: int = 1


@dataclass(frozen=True)
class TenantFairnessPolicy:
    """When selecting work across tenants, cap picks per tenant in one batch."""

    max_items_per_tenant_per_batch: int = 1


def compute_next_eligible_at(attempt_count: int, *, base_delay_seconds: int = 30) -> datetime:
    delay = min(base_delay_seconds * (2**attempt_count), 3600)
    return datetime.now(UTC) + timedelta(seconds=delay)


def retry_metadata_from_row(row: SnapshotRebuildRequirement) -> RetryMetadata:
    return RetryMetadata(
        attempt_count=row.attempt_count,
        max_attempts=row.max_attempts,
        next_eligible_at=row.next_eligible_at,
        last_error=row.last_error,
    )


def is_eligible_for_dispatch(
    row: SnapshotRebuildRequirement,
    *,
    now: datetime | None = None,
) -> bool:
    now = now or datetime.now(UTC)
    if not row.requires_rebuild:
        return False
    if row.orchestration_status in (
        RebuildOrchestrationStatus.RUNNING,
        RebuildOrchestrationStatus.SUCCEEDED,
    ):
        return False
    if row.attempt_count >= row.max_attempts:
        return False
    if row.next_eligible_at is not None and row.next_eligible_at > now:
        return False
    return row.orchestration_status in (
        RebuildOrchestrationStatus.PENDING,
        RebuildOrchestrationStatus.QUEUED,
        RebuildOrchestrationStatus.FAILED,
        RebuildOrchestrationStatus.DEFERRED,
    )


def select_fair_batch(
    rows: list[SnapshotRebuildRequirement],
    *,
    limit: int,
    policy: TenantFairnessPolicy | None = None,
) -> list[SnapshotRebuildRequirement]:
    """Priority sort with per-tenant cap (foundation for future worker scheduler)."""
    policy = policy or TenantFairnessPolicy()
    ordered = sorted(
        rows,
        key=lambda r: (r.priority, r.created_at),
    )
    picked: list[SnapshotRebuildRequirement] = []
    per_tenant: dict[UUID, int] = {}
    for row in ordered:
        if len(picked) >= limit:
            break
        count = per_tenant.get(row.user_id, 0)
        if count >= policy.max_items_per_tenant_per_batch:
            continue
        picked.append(row)
        per_tenant[row.user_id] = count + 1
    return picked


class RebuildOrchestrationService:
    """
    Status transitions for rebuild requirements (no distributed scheduler).

    Future worker should call these inside TenantSession; ops API stays read-only.
    """

    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def mark_queued(self, row: SnapshotRebuildRequirement) -> None:
        row.orchestration_status = RebuildOrchestrationStatus.QUEUED

    async def mark_running(self, row: SnapshotRebuildRequirement) -> None:
        now = datetime.now(UTC)
        row.orchestration_status = RebuildOrchestrationStatus.RUNNING
        row.started_at = now
        row.last_attempted_at = now
        row.attempt_count += 1

    async def mark_succeeded(self, row: SnapshotRebuildRequirement) -> None:
        row.orchestration_status = RebuildOrchestrationStatus.SUCCEEDED
        row.requires_rebuild = False
        row.completed_at = datetime.now(UTC)
        row.last_error = None

    async def mark_failed(self, row: SnapshotRebuildRequirement, *, error: str) -> None:
        row.last_error = error
        row.last_attempted_at = datetime.now(UTC)
        if row.attempt_count >= row.max_attempts:
            row.orchestration_status = RebuildOrchestrationStatus.FAILED
            row.completed_at = datetime.now(UTC)
        else:
            row.orchestration_status = RebuildOrchestrationStatus.DEFERRED
            row.next_eligible_at = compute_next_eligible_at(row.attempt_count)

    async def mark_deferred_lock_busy(
        self,
        row: SnapshotRebuildRequirement,
        *,
        defer_seconds: int = 60,
    ) -> None:
        """Advisory lock held by another session — defer without consuming retry budget."""
        if row.attempt_count > 0:
            row.attempt_count -= 1
        row.orchestration_status = RebuildOrchestrationStatus.DEFERRED
        row.next_eligible_at = datetime.now(UTC) + timedelta(seconds=defer_seconds)
        row.last_error = "inventory rebuild advisory lock busy"
        row.last_attempted_at = datetime.now(UTC)
        row.started_at = None
