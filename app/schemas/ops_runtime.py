"""Operational DTOs for runtime control plane visibility (tenant-scoped)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.runtime.control_plane.state import (
    RuntimeHealthSeverity,
    TenantOperationalState,
    WorkloadState,
)


class HealthDimensionResponse(BaseModel):
    name: str
    score: float
    severity: RuntimeHealthSeverity
    detail: str


class RuntimeHealthResponse(BaseModel):
    overall_score: float
    overall_severity: RuntimeHealthSeverity
    dimensions: list[HealthDimensionResponse]
    recommendations: list[str] = Field(default_factory=list)


class RuntimeQueueSnapshotResponse(BaseModel):
    pending_count: int
    processing_count: int
    dead_letter_count: int
    oldest_pending_lag_seconds: int | None = None


class RuntimeRebuildSnapshotResponse(BaseModel):
    pending_dispatch: int
    deferred: int
    running: int
    failed: int


class RuntimeSummaryResponse(BaseModel):
    tenant_state: TenantOperationalState
    workload_state: WorkloadState
    queue: RuntimeQueueSnapshotResponse
    rebuild: RuntimeRebuildSnapshotResponse
    health: RuntimeHealthResponse
    policy_autonomy_enabled: bool
    policy_queue_overload_threshold: int
