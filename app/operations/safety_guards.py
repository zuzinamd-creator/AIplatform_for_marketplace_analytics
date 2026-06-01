"""Production safety warnings (structured logs only — no vendor alerting)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.observability import get_logger
from app.core.security_context import TenantSession
from app.models.etl.anomaly import EtlAnomaly
from app.models.inventory.integrity import SnapshotConsistencyCheck
from app.models.job import EtlJob, JobStatus

logger = get_logger("production_safety")


@dataclass(frozen=True)
class SafetyCheckResult:
    check: str
    triggered: bool
    value: float | int
    threshold: float | int
    detail: str


def warn_rebuild_duration_high(
    *,
    duration_ms: float,
    user_id: str | None = None,
    rebuild_mode: str = "incremental",
) -> SafetyCheckResult:
    threshold = settings.ops_rebuild_duration_warn_ms
    triggered = duration_ms > threshold
    if triggered:
        logger.warning(
            "ops_rebuild_duration_high",
            extra={
                "user_id": user_id,
                "rebuild_duration_ms": duration_ms,
                "threshold_ms": threshold,
                "rebuild_mode": rebuild_mode,
            },
        )
    return SafetyCheckResult(
        check="rebuild_duration",
        triggered=triggered,
        value=duration_ms,
        threshold=threshold,
        detail="rebuild exceeded duration budget",
    )


def warn_wal_growth_high(
    *,
    wal_bytes_delta: int,
    user_id: str | None = None,
) -> SafetyCheckResult:
    threshold = settings.ops_wal_bytes_delta_warn
    triggered = wal_bytes_delta > threshold
    if triggered:
        logger.warning(
            "ops_wal_growth_high",
            extra={
                "user_id": user_id,
                "wal_bytes_delta": wal_bytes_delta,
                "threshold_bytes": threshold,
            },
        )
    return SafetyCheckResult(
        check="wal_growth",
        triggered=triggered,
        value=wal_bytes_delta,
        threshold=threshold,
        detail="WAL delta exceeded budget",
    )


class ProductionSafetyGuards:
    """Reactive checks — call after operations or from ops runbooks."""

    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def check_queue_lag(self) -> SafetyCheckResult:
        async with TenantSession.transaction(self.db, self.user_id):
            oldest = (
                await self.db.execute(
                    select(func.min(EtlJob.created_at)).where(
                        EtlJob.user_id == self.user_id,
                        EtlJob.status == JobStatus.PENDING,
                    )
                )
            ).scalar_one()
        if oldest is None:
            return SafetyCheckResult(
                check="queue_lag",
                triggered=False,
                value=0,
                threshold=settings.ops_queue_lag_warn_seconds,
                detail="no pending jobs",
            )
        lag_seconds = (datetime.now(UTC) - oldest).total_seconds()
        threshold = settings.ops_queue_lag_warn_seconds
        triggered = lag_seconds > threshold
        if triggered:
            logger.warning(
                "ops_queue_lag_high",
                extra={
                    "user_id": str(self.user_id),
                    "lag_seconds": lag_seconds,
                    "threshold_seconds": threshold,
                },
            )
        return SafetyCheckResult(
            check="queue_lag",
            triggered=triggered,
            value=int(lag_seconds),
            threshold=threshold,
            detail="oldest pending job age",
        )

    async def check_anomaly_explosion(self) -> SafetyCheckResult:
        window = timedelta(hours=settings.ops_anomaly_window_hours)
        since = datetime.now(UTC) - window
        async with TenantSession.transaction(self.db, self.user_id):
            count = (
                await self.db.execute(
                    select(func.count())
                    .select_from(EtlAnomaly)
                    .where(
                        EtlAnomaly.user_id == self.user_id,
                        EtlAnomaly.created_at >= since,
                    )
                )
            ).scalar_one()
        threshold = settings.ops_anomaly_count_warn
        triggered = int(count) > threshold
        if triggered:
            logger.warning(
                "ops_anomaly_explosion",
                extra={
                    "user_id": str(self.user_id),
                    "anomaly_count": int(count),
                    "threshold": threshold,
                    "window_hours": settings.ops_anomaly_window_hours,
                },
            )
        return SafetyCheckResult(
            check="anomaly_explosion",
            triggered=triggered,
            value=int(count),
            threshold=threshold,
            detail=f"anomalies in last {settings.ops_anomaly_window_hours}h",
        )

    async def check_drift_frequency(self) -> SafetyCheckResult:
        window = timedelta(hours=settings.ops_drift_window_hours)
        since = datetime.now(UTC) - window
        async with TenantSession.transaction(self.db, self.user_id):
            count = (
                await self.db.execute(
                    select(func.count())
                    .select_from(SnapshotConsistencyCheck)
                    .where(
                        SnapshotConsistencyCheck.user_id == self.user_id,
                        SnapshotConsistencyCheck.checked_at >= since,
                        SnapshotConsistencyCheck.is_consistent.is_(False),
                    )
                )
            ).scalar_one()
        threshold = settings.ops_drift_fail_warn
        triggered = int(count) > threshold
        if triggered:
            logger.warning(
                "ops_drift_frequency_high",
                extra={
                    "user_id": str(self.user_id),
                    "failed_checks": int(count),
                    "threshold": threshold,
                    "window_hours": settings.ops_drift_window_hours,
                },
            )
        return SafetyCheckResult(
            check="drift_frequency",
            triggered=triggered,
            value=int(count),
            threshold=threshold,
            detail=f"failed drift checks in last {settings.ops_drift_window_hours}h",
        )

    async def read_wal_bytes(self) -> int | None:
        try:
            async with TenantSession.transaction(self.db, self.user_id):
                result = await self.db.execute(text("SELECT wal_bytes FROM pg_stat_wal"))
                row = result.one_or_none()
            return int(row[0]) if row else None
        except Exception as exc:
            logger.warning("ops_wal_read_failed", extra={"error": str(exc)})
            return None

    async def evaluate_tenant_health(self) -> list[SafetyCheckResult]:
        return [
            await self.check_queue_lag(),
            await self.check_anomaly_explosion(),
            await self.check_drift_frequency(),
        ]
