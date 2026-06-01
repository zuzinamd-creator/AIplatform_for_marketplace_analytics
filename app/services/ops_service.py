"""Read-only operational queries (tenant-scoped via RLS)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security_context import TenantSession
from app.core.tenant_context import (
    set_bypass_rls_context,
    set_current_user_context,
    set_queue_role_context,
)
from app.models.enterprise_runtime import (
    AutonomousActionStatus,
    RuntimeAutonomousAction,
    RuntimeSchedulePolicy,
)
from app.models.etl.anomaly import EtlAnomaly
from app.models.inventory.integrity import SnapshotConsistencyCheck
from app.models.job import EtlJob, JobStatus
from app.models.semantics.governance import (
    RebuildOrchestrationStatus,
    SemanticsLifecycleVersion,
    SnapshotRebuildRequirement,
)
from app.models.user import User
from app.runtime.control_plane.coordinator import RuntimeControlPlane
from app.runtime.enterprise.governance import AutonomyPermissionMatrix
from app.runtime.enterprise.scheduling import is_in_blackout
from app.runtime.enterprise.simulation import OperationalSimulationEngine
from app.runtime.health.evaluator import RuntimeHealthEvaluator
from app.runtime.observability import collect_tenant_queue_metrics, collect_tenant_rebuild_metrics
from app.runtime.policy.engine import RuntimeOperationalPolicy
from app.schemas.ops import PageMeta
from app.schemas.ops_enterprise import (
    AutonomyStatusResponse,
    OperationalForecastResponse,
    SchedulePolicyResponse,
    SimulationResponse,
)
from app.schemas.ops_runtime import (
    HealthDimensionResponse,
    RuntimeHealthResponse,
    RuntimeQueueSnapshotResponse,
    RuntimeRebuildSnapshotResponse,
    RuntimeSummaryResponse,
)
from app.services.base import TenantScopedService


class OpsService(TenantScopedService):
    def __init__(self, db: AsyncSession, user: User) -> None:
        super().__init__(db, user_id=user.id)
        self.user = user

    @asynccontextmanager
    async def _tenant_read(self) -> AsyncIterator[None]:
        """RLS context for reads; compatible with session already in a transaction."""
        if self.user_id is None:
            raise ValueError("user_id is required for operational reads")
        user_id = self.user_id
        if self.db.in_transaction():
            await set_bypass_rls_context(self.db, False)
            await set_queue_role_context(self.db, False)
            await set_current_user_context(self.db, user_id)
            yield
        else:
            async with TenantSession.transaction(self.db, user_id):
                yield

    async def list_rebuilds(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        status: str | None = None,
    ) -> tuple[list[SnapshotRebuildRequirement], int]:
        stmt = select(SnapshotRebuildRequirement).order_by(
            SnapshotRebuildRequirement.priority.asc(),
            SnapshotRebuildRequirement.created_at.desc(),
        )
        count_stmt = select(func.count()).select_from(SnapshotRebuildRequirement)
        if status is not None:
            status_enum = RebuildOrchestrationStatus(status)
            stmt = stmt.where(SnapshotRebuildRequirement.orchestration_status == status_enum)
            count_stmt = count_stmt.where(
                SnapshotRebuildRequirement.orchestration_status == status_enum
            )
        stmt = stmt.offset(skip).limit(limit)
        async with self._tenant_read():
            total = (await self.db.execute(count_stmt)).scalar_one()
            rows = list((await self.db.execute(stmt)).scalars().all())
        return rows, int(total)

    async def list_anomalies(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[EtlAnomaly], int]:
        stmt = (
            select(EtlAnomaly)
            .order_by(EtlAnomaly.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_stmt = select(func.count()).select_from(EtlAnomaly)
        async with self._tenant_read():
            total = (await self.db.execute(count_stmt)).scalar_one()
            rows = list((await self.db.execute(stmt)).scalars().all())
        return rows, int(total)

    async def list_drift_checks(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        consistent_only: bool | None = None,
    ) -> tuple[list[SnapshotConsistencyCheck], int]:
        stmt = select(SnapshotConsistencyCheck).order_by(SnapshotConsistencyCheck.checked_at.desc())
        count_stmt = select(func.count()).select_from(SnapshotConsistencyCheck)
        if consistent_only is not None:
            stmt = stmt.where(SnapshotConsistencyCheck.is_consistent == consistent_only)
            count_stmt = count_stmt.where(SnapshotConsistencyCheck.is_consistent == consistent_only)
        stmt = stmt.offset(skip).limit(limit)
        async with self._tenant_read():
            total = (await self.db.execute(count_stmt)).scalar_one()
            rows = list((await self.db.execute(stmt)).scalars().all())
        return rows, int(total)

    async def list_queue_jobs(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        status: JobStatus | None = None,
    ) -> tuple[list[EtlJob], int, dict[str, int]]:
        stmt = select(EtlJob).order_by(EtlJob.created_at.desc())
        count_stmt = select(func.count()).select_from(EtlJob)
        if status is not None:
            stmt = stmt.where(EtlJob.status == status)
            count_stmt = count_stmt.where(EtlJob.status == status)
        stmt = stmt.offset(skip).limit(limit)

        counts_stmt = (
            select(EtlJob.status, func.count())
            .group_by(EtlJob.status)
        )
        async with self._tenant_read():
            total = (await self.db.execute(count_stmt)).scalar_one()
            rows = list((await self.db.execute(stmt)).scalars().all())
            status_rows = (await self.db.execute(counts_stmt)).all()
        status_counts = {row[0].value: int(row[1]) for row in status_rows}
        return rows, int(total), status_counts

    async def list_dead_letter_jobs(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[EtlJob], int]:
        rows, total, _ = await self.list_queue_jobs(
            skip=skip, limit=limit, status=JobStatus.DEAD_LETTER
        )
        return rows, total

    async def semantics_status(self) -> list[SemanticsLifecycleVersion]:
        stmt = select(SemanticsLifecycleVersion).order_by(SemanticsLifecycleVersion.version.asc())
        async with self._tenant_read():
            return list((await self.db.execute(stmt)).scalars().all())

    async def runtime_health(self) -> RuntimeHealthResponse:
        user_id = self.user_id
        if user_id is None:
            raise ValueError("user_id is required for runtime health")
        async with self._tenant_read():
            queue = await collect_tenant_queue_metrics(self.db, user_id)
            rebuild = await collect_tenant_rebuild_metrics(self.db, user_id)
        report = RuntimeHealthEvaluator().evaluate(queue=queue, rebuild=rebuild)
        return RuntimeHealthResponse(
            overall_score=report.overall_score,
            overall_severity=report.overall_severity,
            dimensions=[
                HealthDimensionResponse(
                    name=d.name,
                    score=d.score,
                    severity=d.severity,
                    detail=d.detail,
                )
                for d in report.dimensions
            ],
            recommendations=list(report.recommendations),
        )

    async def runtime_summary(self) -> RuntimeSummaryResponse:
        user_id = self.user_id
        if user_id is None:
            raise ValueError("user_id is required for runtime summary")
        policy = RuntimeOperationalPolicy.from_settings()
        async with self._tenant_read():
            queue = await collect_tenant_queue_metrics(self.db, user_id)
            rebuild = await collect_tenant_rebuild_metrics(self.db, user_id)
        report = RuntimeHealthEvaluator().evaluate(queue=queue, rebuild=rebuild)
        health = RuntimeHealthResponse(
            overall_score=report.overall_score,
            overall_severity=report.overall_severity,
            dimensions=[
                HealthDimensionResponse(
                    name=d.name,
                    score=d.score,
                    severity=d.severity,
                    detail=d.detail,
                )
                for d in report.dimensions
            ],
            recommendations=list(report.recommendations),
        )
        snapshot = RuntimeControlPlane(self.db, policy=policy).snapshot_from_metrics(
            queue, rebuild, report
        )
        return RuntimeSummaryResponse(
            tenant_state=snapshot.tenant_state,
            workload_state=snapshot.workload_state,
            queue=RuntimeQueueSnapshotResponse(
                pending_count=queue.pending_count,
                processing_count=queue.processing_count,
                dead_letter_count=queue.dead_letter_count,
                oldest_pending_lag_seconds=queue.oldest_pending_lag_seconds,
            ),
            rebuild=RuntimeRebuildSnapshotResponse(
                pending_dispatch=rebuild.pending_dispatch,
                deferred=rebuild.deferred,
                running=rebuild.running,
                failed=rebuild.failed,
            ),
            health=health,
            policy_autonomy_enabled=policy.autonomy_enabled,
            policy_queue_overload_threshold=policy.queue_overload_threshold,
        )

    async def autonomy_status(self) -> AutonomyStatusResponse:
        async with self._tenant_read():
            pending = (
                await self.db.execute(
                    select(func.count())
                    .select_from(RuntimeAutonomousAction)
                    .where(RuntimeAutonomousAction.status == AutonomousActionStatus.PLANNED)
                )
            ).scalar_one()
        recs: list[str] = []
        if AutonomyPermissionMatrix.emergency_stop_active():
            recs.append("Emergency stop: RUNTIME_AUTONOMY disabled via kill switch.")
        return AutonomyStatusResponse(
            safety_level=AutonomyPermissionMatrix.safety_level().value,
            emergency_stop_active=AutonomyPermissionMatrix.emergency_stop_active(),
            enterprise_ops_enabled=settings.runtime_enterprise_ops_enabled,
            autonomy_enabled=RuntimeOperationalPolicy.from_settings().autonomy_enabled,
            pending_journal_entries=int(pending),
            recommendations=recs,
        )

    async def operational_forecast(self) -> OperationalForecastResponse:
        user_id = self.user_id
        if user_id is None:
            raise ValueError("user_id required")
        async with self._tenant_read():
            queue = await collect_tenant_queue_metrics(self.db, user_id)
            rebuild = await collect_tenant_rebuild_metrics(self.db, user_id)
        report = RuntimeHealthEvaluator().evaluate(queue=queue, rebuild=rebuild)
        policy = RuntimeOperationalPolicy.from_settings()
        from app.runtime.enterprise.forecasting import RuntimeIntelligenceEngine

        forecast = RuntimeIntelligenceEngine().forecast(
            queue=queue, rebuild=rebuild, health=report, policy=policy
        )
        return OperationalForecastResponse(
            queue_saturation_score=forecast.queue_saturation_score,
            rebuild_pressure_score=forecast.rebuild_pressure_score,
            overload_risk=forecast.overload_risk,
            autonomy_health_score=forecast.autonomy_health_score,
            ai_execution_pressure=forecast.ai_execution_pressure,
            drift_score=forecast.drift_score,
            recommendations=list(forecast.recommendations),
        )

    async def run_simulation(self, scenario: str = "full_cycle") -> SimulationResponse:
        engine = OperationalSimulationEngine(self.db)
        result = await engine.simulate_cycle()
        return SimulationResponse(
            dry_run=True,
            forecast=OperationalForecastResponse(
                queue_saturation_score=result.forecast.queue_saturation_score,
                rebuild_pressure_score=result.forecast.rebuild_pressure_score,
                overload_risk=result.forecast.overload_risk,
                autonomy_health_score=result.forecast.autonomy_health_score,
                ai_execution_pressure=result.forecast.ai_execution_pressure,
                drift_score=result.forecast.drift_score,
                recommendations=list(result.forecast.recommendations),
            ),
            executed_steps=result.remediation.executed_steps,
            blocked_steps=result.remediation.blocked_steps,
            detail=result.remediation.detail,
        )

    async def list_remediation_history(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[RuntimeAutonomousAction], int]:
        stmt = (
            select(RuntimeAutonomousAction)
            .order_by(RuntimeAutonomousAction.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        count_stmt = select(func.count()).select_from(RuntimeAutonomousAction)
        async with self._tenant_read():
            total = (await self.db.execute(count_stmt)).scalar_one()
            rows = list((await self.db.execute(stmt)).scalars().all())
        return rows, int(total)

    async def schedule_policy(self) -> SchedulePolicyResponse:
        user_id = self.user_id
        if user_id is None:
            raise ValueError("user_id required")
        async with self._tenant_read():
            row = (
                await self.db.execute(
                    select(RuntimeSchedulePolicy).where(RuntimeSchedulePolicy.user_id == user_id)
                )
            ).scalar_one_or_none()
        blackout = row.blackout_periods if row else None
        periods = None
        if isinstance(blackout, dict):
            periods = blackout.get("periods")
        elif isinstance(blackout, list):
            periods = blackout
        return SchedulePolicyResponse(
            maintenance_windows=row.maintenance_windows if row else None,
            blackout_periods=row.blackout_periods if row else None,
            fairness_weight=row.fairness_weight if row else None,
            rebuild_priority_bias=row.rebuild_priority_bias if row else None,
            adaptive_rebuild_enabled=row.adaptive_rebuild_enabled if row else True,
            in_blackout=is_in_blackout(blackout_periods=periods),
        )

    @staticmethod
    def page_meta(total: int, skip: int, limit: int) -> PageMeta:
        return PageMeta(total=total, skip=skip, limit=limit)
