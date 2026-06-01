"""Tenant isolation guards — quarantine poison tenants."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security_context import DispatchSession, TenantSession
from app.models.job import EtlJob, JobStatus
from app.models.reliability import TenantContainmentState, TenantContainmentStatus
from app.runtime.metrics import emit_runtime_metric


@dataclass(frozen=True)
class TenantGuardResult:
    allowed: bool
    status: TenantContainmentStatus
    reason: str


class TenantContainmentGuard:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def check(self, user_id: UUID, *, in_transaction: bool = False) -> TenantGuardResult:
        if in_transaction:
            row = await self.db.get(TenantContainmentState, user_id)
            return self._result_from_row(row)

        async with DispatchSession.transaction(self.db):
            row = await self.db.get(TenantContainmentState, user_id)
        return self._result_from_row(row)

    def _result_from_row(self, row: TenantContainmentState | None) -> TenantGuardResult:
        if row is None:
            return TenantGuardResult(True, TenantContainmentStatus.HEALTHY, "healthy")
        status = TenantContainmentStatus(row.status)
        if status == TenantContainmentStatus.QUARANTINED:
            return TenantGuardResult(False, status, row.reason or "quarantined")
        if status == TenantContainmentStatus.THROTTLED:
            if row.throttled_until and row.throttled_until > datetime.now(UTC):
                return TenantGuardResult(False, status, row.reason or "throttled")
        return TenantGuardResult(True, status, row.reason or "healthy")

    async def evaluate_and_apply_quarantine(self, user_id: UUID) -> TenantGuardResult:
        async with TenantSession.transaction(self.db, user_id):
            dlq_count = (
                await self.db.execute(
                    select(func.count())
                    .select_from(EtlJob)
                    .where(EtlJob.user_id == user_id, EtlJob.status == JobStatus.DEAD_LETTER)
                )
            ).scalar_one()
            pending = (
                await self.db.execute(
                    select(func.count())
                    .select_from(EtlJob)
                    .where(EtlJob.user_id == user_id, EtlJob.status == JobStatus.PENDING)
                )
            ).scalar_one()

        if int(dlq_count) >= settings.reliability_tenant_quarantine_dlq_threshold:
            return await self._set_status(
                user_id,
                TenantContainmentStatus.QUARANTINED,
                f"dlq_count={dlq_count} exceeds threshold",
            )
        if int(pending) >= settings.reliability_tenant_throttle_pending_jobs:
            throttled_until = datetime.now(UTC) + timedelta(
                seconds=settings.reliability_tenant_throttle_duration_seconds
            )
            return await self._set_status(
                user_id,
                TenantContainmentStatus.THROTTLED,
                f"pending_jobs={pending}",
                throttled_until=throttled_until,
            )
        return TenantGuardResult(True, TenantContainmentStatus.HEALTHY, "healthy")

    async def _set_status(
        self,
        user_id: UUID,
        status: TenantContainmentStatus,
        reason: str,
        *,
        throttled_until: datetime | None = None,
    ) -> TenantGuardResult:
        async with DispatchSession.transaction(self.db):
            row = await self.db.get(TenantContainmentState, user_id)
            if row is None:
                row = TenantContainmentState(
                    user_id=user_id,
                    status=status,
                    reason=reason,
                    throttled_until=throttled_until,
                )
                self.db.add(row)
            else:
                row.status = status
                row.reason = reason
                row.throttled_until = throttled_until
            await self.db.flush()
        emit_runtime_metric(
            "runtime_tenant_containment",
            user_id=str(user_id),
            status=status.value,
            reason=reason,
        )
        return TenantGuardResult(False, status, reason)
