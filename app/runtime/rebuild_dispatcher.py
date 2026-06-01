"""Rebuild requirement dispatcher — fair, throttled, advisory-lock aware."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.observability import clear_context
from app.core.observability.etl_metrics import bind_log_context, record_metrics
from app.core.security_context import DispatchSession, TenantSession
from app.domain.inventory.errors import InventoryRebuildBusyError, UnsupportedSemanticsVersionError
from app.domain.semantics.governance_policy import assert_rebuild_allowed
from app.etl.wb.full_inventory_rebuild import FullInventoryRebuildService
from app.etl.wb.inventory_snapshot_rebuild import InventorySnapshotRebuildService
from app.models.semantics.governance import (
    RebuildMode,
    RebuildOrchestrationStatus,
    SnapshotRebuildRequirement,
)
from app.operations.rebuild_orchestration import (
    RebuildOrchestrationService,
    TenantFairnessPolicy,
    is_eligible_for_dispatch,
    select_fair_batch,
)
from app.runtime.adaptive.prioritizer import AdaptiveRebuildPrioritizer
from app.runtime.containment.tenant_guard import TenantContainmentGuard
from app.runtime.metrics import emit_runtime_metric
from app.runtime.policy.engine import RuntimeOperationalPolicy
from app.runtime.reliability.circuit_breaker import GLOBAL_CIRCUIT_BREAKERS
from app.runtime.reliability.kill_switches import KillSwitchDomain, RuntimeKillSwitches
from app.runtime.runtime_guards import (
    RuntimeGuardState,
    record_busy_defer,
    record_dispatch_success,
    record_rebuild_completed,
)
from app.runtime.tracing import bind_rebuild_trace, new_rebuild_trace_id


@dataclass(frozen=True)
class RebuildDispatchResult:
    dispatched: bool
    requirement_id: UUID | None
    user_id: UUID | None
    outcome: str
    detail: str


class RebuildDispatcher:
    """
    Claims eligible snapshot_rebuild_requirements and executes rebuild in TenantSession.

    Cross-tenant selection uses DispatchSession (queue_role read).
    Mutations and rebuild execution use TenantSession per row.user_id.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        guard_state: RuntimeGuardState | None = None,
    ) -> None:
        self.db = db
        self._guard_state = guard_state or RuntimeGuardState()
        self._policy = RuntimeOperationalPolicy.from_settings()
        self._prioritizer = AdaptiveRebuildPrioritizer()

    async def dispatch_once(self) -> RebuildDispatchResult:
        switch = RuntimeKillSwitches.check(KillSwitchDomain.REBUILD_DISPATCH)
        if not switch.allowed:
            return RebuildDispatchResult(
                dispatched=False,
                requirement_id=None,
                user_id=None,
                outcome="blocked",
                detail=switch.reason,
            )
        if not GLOBAL_CIRCUIT_BREAKERS.allow("rebuild_dispatch"):
            return RebuildDispatchResult(
                dispatched=False,
                requirement_id=None,
                user_id=None,
                outcome="circuit_open",
                detail="rebuild dispatch circuit open",
            )
        requirement_id = await self._select_requirement_id()
        if requirement_id is None:
            return RebuildDispatchResult(
                dispatched=False,
                requirement_id=None,
                user_id=None,
                outcome="idle",
                detail="no eligible rebuild requirements",
            )
        return await self._execute_requirement(requirement_id)

    async def _select_requirement_id(self) -> UUID | None:
        now = datetime.now(UTC)
        async with DispatchSession.transaction(self.db):
            result = await self.db.execute(
                select(SnapshotRebuildRequirement)
                .where(SnapshotRebuildRequirement.requires_rebuild.is_(True))
                .where(
                    SnapshotRebuildRequirement.orchestration_status.in_(
                        (
                            RebuildOrchestrationStatus.PENDING,
                            RebuildOrchestrationStatus.QUEUED,
                            RebuildOrchestrationStatus.DEFERRED,
                            RebuildOrchestrationStatus.FAILED,
                        )
                    )
                )
                .order_by(
                    SnapshotRebuildRequirement.priority.asc(),
                    SnapshotRebuildRequirement.created_at.asc(),
                )
                .limit(settings.orchestrator_dispatch_batch_size)
            )
            candidates = [r for r in result.scalars().all() if is_eligible_for_dispatch(r, now=now)]
            if not candidates:
                return None
            candidates = self._prioritizer.adjust(candidates)
            batch = select_fair_batch(
                candidates,
                limit=settings.orchestrator_max_dispatch_per_cycle,
                policy=TenantFairnessPolicy(),
            )
            if not batch:
                return None
            return batch[0].id

    async def _execute_requirement(self, requirement_id: UUID) -> RebuildDispatchResult:
        user_id: UUID

        async with DispatchSession.transaction(self.db):
            peek = await self.db.get(SnapshotRebuildRequirement, requirement_id)
            if peek is None or not is_eligible_for_dispatch(peek):
                return RebuildDispatchResult(
                    dispatched=False,
                    requirement_id=requirement_id,
                    user_id=None,
                    outcome="skipped",
                    detail="requirement no longer eligible",
                )
            user_id = peek.user_id
            guard = await TenantContainmentGuard(self.db).check(user_id, in_transaction=True)
            if not guard.allowed:
                return RebuildDispatchResult(
                    dispatched=False,
                    requirement_id=requirement_id,
                    user_id=user_id,
                    outcome="tenant_contained",
                    detail=guard.reason,
                )

        trace_id = new_rebuild_trace_id()
        bind_rebuild_trace(trace_id=trace_id, requirement_id=requirement_id, user_id=user_id)
        bind_log_context(
            user_id=str(user_id),
            operation_stage="rebuild_dispatch",
            semantics_version=None,
            rebuild_window=None,
        )

        async with TenantSession.transaction(self.db, user_id):
            row = await self.db.get(SnapshotRebuildRequirement, requirement_id)
            if row is None or not is_eligible_for_dispatch(row):
                clear_context()
                return RebuildDispatchResult(
                    dispatched=False,
                    requirement_id=requirement_id,
                    user_id=user_id,
                    outcome="skipped",
                    detail="lost race or ineligible",
                )
            orch = RebuildOrchestrationService(self.db, user_id)
            await orch.mark_queued(row)
            await orch.mark_running(row)
            rebuild_mode = row.rebuild_mode
            semantics_version = row.semantics_version
            priority = row.priority
            attempt_count = row.attempt_count
            if self._policy.should_escalate_to_full(
                attempt_count=attempt_count,
                current_mode=rebuild_mode.value,
            ):
                row.rebuild_mode = RebuildMode.FULL
                rebuild_mode = RebuildMode.FULL
                await self.db.flush()

        emit_runtime_metric(
            "runtime_rebuild_dispatched",
            user_id=str(user_id),
            requirement_id=str(requirement_id),
            rebuild_mode=rebuild_mode.value,
            priority=priority,
            attempt_count=attempt_count,
        )

        try:
            assert_rebuild_allowed(semantics_version)
            async with TenantSession.transaction(self.db, user_id):
                if rebuild_mode == RebuildMode.FULL:
                    await FullInventoryRebuildService(self.db, user_id).rebuild()
                else:
                    await InventorySnapshotRebuildService(self.db, user_id).rebuild()
                orch = RebuildOrchestrationService(self.db, user_id)
                refreshed = await self.db.get(SnapshotRebuildRequirement, requirement_id)
                if refreshed is not None:
                    await orch.mark_succeeded(refreshed)

            record_dispatch_success(self._guard_state)
            record_rebuild_completed(self._guard_state)
            GLOBAL_CIRCUIT_BREAKERS.success("rebuild_dispatch")
            emit_runtime_metric(
                "runtime_rebuild_succeeded",
                user_id=str(user_id),
                requirement_id=str(requirement_id),
                rebuild_mode=rebuild_mode.value,
            )
            clear_context()
            return RebuildDispatchResult(
                dispatched=True,
                requirement_id=requirement_id,
                user_id=user_id,
                outcome="succeeded",
                detail="rebuild completed",
            )
        except InventoryRebuildBusyError:
            record_metrics(advisory_lock_contention=1)
            record_busy_defer(self._guard_state)
            async with TenantSession.transaction(self.db, user_id):
                refreshed = await self.db.get(SnapshotRebuildRequirement, requirement_id)
                if refreshed is not None:
                    orch = RebuildOrchestrationService(self.db, user_id)
                    await orch.mark_deferred_lock_busy(
                        refreshed,
                        defer_seconds=settings.orchestrator_defer_busy_seconds,
                    )
            emit_runtime_metric(
                "runtime_rebuild_deferred_busy",
                user_id=str(user_id),
                requirement_id=str(requirement_id),
            )
            clear_context()
            return RebuildDispatchResult(
                dispatched=True,
                requirement_id=requirement_id,
                user_id=user_id,
                outcome="deferred_busy",
                detail="advisory lock not acquired",
            )
        except UnsupportedSemanticsVersionError as exc:
            async with TenantSession.transaction(self.db, user_id):
                refreshed = await self.db.get(SnapshotRebuildRequirement, requirement_id)
                if refreshed is not None:
                    orch = RebuildOrchestrationService(self.db, user_id)
                    await orch.mark_failed(refreshed, error=str(exc))
            emit_runtime_metric(
                "runtime_rebuild_failed",
                user_id=str(user_id),
                requirement_id=str(requirement_id),
                error=str(exc),
            )
            clear_context()
            return RebuildDispatchResult(
                dispatched=True,
                requirement_id=requirement_id,
                user_id=user_id,
                outcome="failed",
                detail=str(exc),
            )
        except Exception as exc:
            GLOBAL_CIRCUIT_BREAKERS.failure("rebuild_dispatch")
            async with TenantSession.transaction(self.db, user_id):
                refreshed = await self.db.get(SnapshotRebuildRequirement, requirement_id)
                if refreshed is not None:
                    orch = RebuildOrchestrationService(self.db, user_id)
                    await orch.mark_failed(refreshed, error=str(exc))
            emit_runtime_metric(
                "runtime_rebuild_failed",
                user_id=str(user_id),
                requirement_id=str(requirement_id),
                error=str(exc),
            )
            clear_context()
            return RebuildDispatchResult(
                dispatched=True,
                requirement_id=requirement_id,
                user_id=user_id,
                outcome="failed",
                detail=str(exc),
            )
