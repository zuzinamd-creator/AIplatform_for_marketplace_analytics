"""Structured runtime event taxonomy."""

from __future__ import annotations

from enum import StrEnum


class RuntimeEventCategory(StrEnum):
    QUEUE = "queue"
    REBUILD = "rebuild"
    ORCHESTRATION = "orchestration"
    AUTONOMY = "autonomy"
    RELIABILITY = "reliability"
    AI = "ai"
    OPERATOR = "operator"


class RuntimeEventName(StrEnum):
    JOB_CLAIMED = "job_claimed"
    JOB_COMPLETED = "job_completed"
    JOB_DEAD_LETTERED = "job_dead_lettered"
    REBUILD_DISPATCHED = "runtime_rebuild_dispatched"
    REBUILD_SUCCEEDED = "runtime_rebuild_succeeded"
    REBUILD_DEFERRED_BUSY = "runtime_rebuild_deferred_busy"
    QUEUE_OVERLOAD = "runtime_queue_overload_warning"
    CIRCUIT_OPENED = "runtime_circuit_opened"
    CIRCUIT_CLOSED = "runtime_circuit_closed"
    LEASE_ACQUIRED = "runtime_lease_acquired"
    LEASE_DENIED = "runtime_lease_denied"
    PROCESS_HEARTBEAT = "runtime_process_heartbeat"
    TENANT_CONTAINMENT = "runtime_tenant_containment"
    AUTONOMY_ACTION = "runtime_autonomy_action"
    DEGRADATION = "runtime_degradation_state"
    AI_PROVIDER_FAILOVER = "ai_provider_failover"
    OPERATOR_ACTION = "operator_audit_action"
