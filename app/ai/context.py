"""Context assembly with semantics and operational health gates."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.metrics import emit_ai_metric
from app.core.config import settings
from app.core.security_context import TenantSession
from app.domain.semantics.governance_policy import assert_rebuild_allowed, get_lifecycle_record
from app.dto.analytics_dto import AIInsightInputDTO
from app.models.semantics.governance import RebuildOrchestrationStatus, SnapshotRebuildRequirement


@dataclass(frozen=True)
class AIExecutionContext:
    """Immutable context package passed to agent executors."""

    user_id: UUID
    semantics_version: str
    data_as_of: datetime
    context_valid: bool
    invalid_reason: str | None
    rebuild_pending_count: int
    rebuild_running_count: int
    insight_input: AIInsightInputDTO | None
    degraded_mode: bool
    governed_extras: dict = field(default_factory=dict)


class AIContextAssembler:
    """Builds governed context; blocks invalid semantics for probabilistic generation."""

    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def assemble(
        self,
        *,
        semantics_version: str,
        insight_input: AIInsightInputDTO | None = None,
        governed_extras: dict | None = None,
    ) -> AIExecutionContext:
        now = datetime.now(UTC)
        invalid_reason: str | None = None
        context_valid = True
        degraded = False

        try:
            record = get_lifecycle_record(semantics_version)
            if not record.supported_for_rebuild:
                context_valid = False
                invalid_reason = (
                    f"semantics {semantics_version} not supported for analytics context"
                )
            else:
                assert_rebuild_allowed(semantics_version)
        except Exception as exc:
            context_valid = False
            invalid_reason = str(exc)

        pending, running = await self._rebuild_counts()
        if running > 0 and insight_input is not None:
            degraded = True
            emit_ai_metric(
                "ai_context_degraded_rebuild_running",
                user_id=str(self.user_id),
                rebuild_running=running,
            )
        if pending > settings.ai_stale_rebuild_pending_warn and insight_input is not None:
            degraded = True
            emit_ai_metric(
                "ai_context_stale_data_warning",
                user_id=str(self.user_id),
                rebuild_pending=pending,
            )

        if not context_valid:
            emit_ai_metric(
                "ai_context_invalid",
                user_id=str(self.user_id),
                reason=invalid_reason,
            )

        return AIExecutionContext(
            user_id=self.user_id,
            semantics_version=semantics_version,
            data_as_of=now,
            context_valid=context_valid,
            invalid_reason=invalid_reason,
            rebuild_pending_count=pending,
            rebuild_running_count=running,
            insight_input=insight_input if context_valid else None,
            degraded_mode=degraded or not settings.ai_enabled,
            governed_extras=dict(governed_extras or {}),
        )

    async def _rebuild_counts(self) -> tuple[int, int]:
        async with TenantSession.transaction(self.db, self.user_id):
            pending = (
                await self.db.execute(
                    select(func.count())
                    .select_from(SnapshotRebuildRequirement)
                    .where(
                        SnapshotRebuildRequirement.user_id == self.user_id,
                        SnapshotRebuildRequirement.requires_rebuild.is_(True),
                        SnapshotRebuildRequirement.orchestration_status.in_(
                            (
                                RebuildOrchestrationStatus.PENDING,
                                RebuildOrchestrationStatus.QUEUED,
                                RebuildOrchestrationStatus.DEFERRED,
                            )
                        ),
                    )
                )
            ).scalar_one()
            running = (
                await self.db.execute(
                    select(func.count())
                    .select_from(SnapshotRebuildRequirement)
                    .where(
                        SnapshotRebuildRequirement.user_id == self.user_id,
                        SnapshotRebuildRequirement.orchestration_status
                        == RebuildOrchestrationStatus.RUNNING,
                    )
                )
            ).scalar_one()
        return int(pending), int(running)
