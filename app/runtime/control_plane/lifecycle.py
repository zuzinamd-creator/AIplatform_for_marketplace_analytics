"""Documented lifecycle transitions for control plane states."""

from __future__ import annotations

from app.runtime.control_plane.state import (
    RuntimeHealthSeverity,
    SchedulingState,
    TenantOperationalState,
    WorkloadState,
)

# Tenant operational transitions (observed, not persisted as enum column)
TENANT_OPERATIONAL_TRANSITIONS: dict[TenantOperationalState, frozenset[TenantOperationalState]] = {
    TenantOperationalState.HEALTHY: frozenset(
        {
            TenantOperationalState.DEGRADED,
            TenantOperationalState.REBUILD_PRESSURE,
            TenantOperationalState.OVERLOADED,
        }
    ),
    TenantOperationalState.DEGRADED: frozenset(
        {TenantOperationalState.HEALTHY, TenantOperationalState.RECOVERY_ACTIVE}
    ),
    TenantOperationalState.REBUILD_PRESSURE: frozenset(
        {TenantOperationalState.HEALTHY, TenantOperationalState.DEGRADED}
    ),
    TenantOperationalState.OVERLOADED: frozenset(
        {TenantOperationalState.DEGRADED, TenantOperationalState.RECOVERY_ACTIVE}
    ),
    TenantOperationalState.RECOVERY_ACTIVE: frozenset(
        {TenantOperationalState.HEALTHY, TenantOperationalState.DEGRADED}
    ),
}

WORKLOAD_TRANSITIONS: dict[WorkloadState, frozenset[WorkloadState]] = {
    WorkloadState.IDLE: frozenset({WorkloadState.DISPATCHING, WorkloadState.MAINTENANCE}),
    WorkloadState.DISPATCHING: frozenset({WorkloadState.IDLE, WorkloadState.THROTTLED}),
    WorkloadState.MAINTENANCE: frozenset({WorkloadState.IDLE}),
    WorkloadState.THROTTLED: frozenset({WorkloadState.IDLE, WorkloadState.DISPATCHING}),
    WorkloadState.PROCESSING: frozenset({WorkloadState.IDLE}),
}

SCHEDULING_TRANSITIONS: dict[SchedulingState, frozenset[SchedulingState]] = {
    SchedulingState.IDLE: frozenset({SchedulingState.DUE}),
    SchedulingState.DUE: frozenset({SchedulingState.RUNNING, SchedulingState.SKIPPED}),
    SchedulingState.RUNNING: frozenset({SchedulingState.COMPLETED, SchedulingState.SKIPPED}),
    SchedulingState.COMPLETED: frozenset({SchedulingState.IDLE}),
    SchedulingState.SKIPPED: frozenset({SchedulingState.IDLE}),
}

HEALTH_SEVERITY_ORDER = (
    RuntimeHealthSeverity.OK,
    RuntimeHealthSeverity.WARN,
    RuntimeHealthSeverity.CRITICAL,
)
