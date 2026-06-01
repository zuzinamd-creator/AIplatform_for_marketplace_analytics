"""Worker/orchestrator liveness registry (PostgreSQL-backed)."""

from __future__ import annotations

import socket
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security_context import DispatchSession
from app.models.reliability import ProcessKind, RuntimeProcessHeartbeat
from app.runtime.metrics import emit_runtime_metric


class ProcessSupervisorRegistry:
    def __init__(self, db: AsyncSession, *, process_id: UUID | None = None) -> None:
        self.db = db
        self.process_id = process_id or uuid4()

    async def heartbeat(
        self,
        kind: ProcessKind,
        *,
        metadata: dict | None = None,
    ) -> UUID:
        now = datetime.now(UTC)
        async with DispatchSession.transaction(self.db):
            row = await self.db.get(RuntimeProcessHeartbeat, self.process_id)
            if row is None:
                row = RuntimeProcessHeartbeat(
                    process_id=self.process_id,
                    process_kind=kind.value,
                    host=socket.gethostname(),
                    last_seen_at=now,
                    metadata_json=metadata,
                )
                self.db.add(row)
            else:
                row.last_seen_at = now
                row.metadata_json = metadata
            await self.db.flush()
        emit_runtime_metric(
            "runtime_process_heartbeat",
            process_id=str(self.process_id),
            process_kind=kind.value,
        )
        return self.process_id

    async def cleanup_stale(self) -> int:
        cutoff = datetime.now(UTC) - timedelta(seconds=settings.reliability_process_stale_seconds)
        async with DispatchSession.transaction(self.db):
            result = await self.db.execute(
                delete(RuntimeProcessHeartbeat).where(RuntimeProcessHeartbeat.last_seen_at < cutoff)
            )
            count = int(getattr(result, "rowcount", 0) or 0)
        if count:
            emit_runtime_metric("runtime_process_stale_cleaned", removed=count)
        return count

    async def list_live(self, kind: ProcessKind | None = None) -> list[RuntimeProcessHeartbeat]:
        cutoff = datetime.now(UTC) - timedelta(seconds=settings.reliability_process_stale_seconds)
        stmt = select(RuntimeProcessHeartbeat).where(RuntimeProcessHeartbeat.last_seen_at >= cutoff)
        if kind is not None:
            stmt = stmt.where(RuntimeProcessHeartbeat.process_kind == kind.value)
        async with DispatchSession.transaction(self.db):
            return list((await self.db.execute(stmt)).scalars().all())
