"""Control plane state models (explicit, PostgreSQL-centric)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class TenantOperationalState(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OVERLOADED = "overloaded"
    REBUILD_PRESSURE = "rebuild_pressure"
    RECOVERY_ACTIVE = "recovery_active"


class WorkloadState(StrEnum):
    IDLE = "idle"
    DISPATCHING = "dispatching"
    PROCESSING = "processing"
    MAINTENANCE = "maintenance"
    THROTTLED = "throttled"


class RuntimeHealthSeverity(StrEnum):
    OK = "ok"
    WARN = "warn"
    CRITICAL = "critical"


class SchedulingState(StrEnum):
    IDLE = "idle"
    DUE = "due"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class ControlPlaneSnapshot:
    """Point-in-time operational view for operators and autonomy."""

    tenant_state: TenantOperationalState
    workload_state: WorkloadState
    health_score: float
    health_severity: RuntimeHealthSeverity
    queue_pending: int
    rebuild_backlog: int
    rebuild_running: int
    autonomy_actions_last_hour: int = 0
    recommendations: tuple[str, ...] = field(default_factory=tuple)
