"""Queue snapshot rebuild requirements without blocking requests."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.observability import get_logger
from app.models.semantics.governance import (
    RebuildMode,
    RebuildOrchestrationStatus,
    SnapshotRebuildRequirement,
)
from app.operations.rebuild_orchestration import RebuildPriority

logger = get_logger(__name__)


class SemanticsInvalidationService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def request_rebuild(
        self,
        *,
        semantics_version: str,
        reason: str,
    ) -> SnapshotRebuildRequirement:
        """
        Persist requires_rebuild flag; background worker should consume the queue.

        Does NOT run rebuild inline — avoids lock contention on user path.
        """
        row = SnapshotRebuildRequirement(
            id=uuid4(),
            user_id=self.user_id,
            semantics_version=semantics_version,
            reason=reason,
            requires_rebuild=True,
            orchestration_status=RebuildOrchestrationStatus.PENDING,
            rebuild_mode=RebuildMode.INCREMENTAL,
            priority=RebuildPriority.SEMANTICS_INVALIDATION,
        )
        self.db.add(row)
        await self.db.flush()
        logger.info(
            "snapshot_rebuild_queued",
            extra={
                "user_id": str(self.user_id),
                "semantics_version": semantics_version,
                "operation_stage": "semantics_invalidation",
                "requires_rebuild": True,
            },
        )
        return row
