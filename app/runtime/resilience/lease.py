"""Orchestrator singleton lease — PostgreSQL ownership model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security_context import DispatchSession
from app.models.reliability import RuntimeProcessLease
from app.runtime.metrics import emit_runtime_metric

ORCHESTRATOR_LEASE_NAME = "orchestrator_primary"


@dataclass(frozen=True)
class LeaseAcquisition:
    acquired: bool
    holder_id: UUID
    reason: str


class OrchestratorLeaseService:
    def __init__(self, db: AsyncSession, *, holder_id: UUID | None = None) -> None:
        self.db = db
        self.holder_id = holder_id or uuid4()

    async def try_acquire(self) -> LeaseAcquisition:
        now = datetime.now(UTC)
        expires = now + timedelta(seconds=settings.reliability_orchestrator_lease_ttl_seconds)
        async with DispatchSession.transaction(self.db):
            row = await self.db.get(RuntimeProcessLease, ORCHESTRATOR_LEASE_NAME)
            if row is None:
                self.db.add(
                    RuntimeProcessLease(
                        lease_name=ORCHESTRATOR_LEASE_NAME,
                        holder_id=self.holder_id,
                        acquired_at=now,
                        expires_at=expires,
                    )
                )
                await self.db.flush()
                emit_runtime_metric("runtime_lease_acquired", holder_id=str(self.holder_id))
                return LeaseAcquisition(True, self.holder_id, "new lease")

            if row.holder_id == self.holder_id or row.expires_at <= now:
                row.holder_id = self.holder_id
                row.acquired_at = now
                row.expires_at = expires
                await self.db.flush()
                emit_runtime_metric("runtime_lease_renewed", holder_id=str(self.holder_id))
                return LeaseAcquisition(True, self.holder_id, "renewed lease")

        emit_runtime_metric(
            "runtime_lease_denied",
            holder_id=str(self.holder_id),
            current_holder=str(row.holder_id),
        )
        return LeaseAcquisition(False, self.holder_id, "held by another process")

    async def release(self) -> None:
        async with DispatchSession.transaction(self.db):
            row = await self.db.get(RuntimeProcessLease, ORCHESTRATOR_LEASE_NAME)
            if row and row.holder_id == self.holder_id:
                await self.db.delete(row)
                await self.db.flush()
                emit_runtime_metric("runtime_lease_released", holder_id=str(self.holder_id))

    async def current_holder(self) -> UUID | None:
        async with DispatchSession.transaction(self.db):
            row = await self.db.get(RuntimeProcessLease, ORCHESTRATOR_LEASE_NAME)
            if row is None or row.expires_at <= datetime.now(UTC):
                return None
            return row.holder_id

    async def snapshot(self) -> RuntimeProcessLease | None:
        async with DispatchSession.transaction(self.db):
            return await self.db.get(RuntimeProcessLease, ORCHESTRATOR_LEASE_NAME)
