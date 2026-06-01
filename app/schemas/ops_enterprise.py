"""Enterprise runtime operations API schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OperationalForecastResponse(BaseModel):
    queue_saturation_score: Decimal
    rebuild_pressure_score: Decimal
    overload_risk: Decimal
    autonomy_health_score: Decimal
    ai_execution_pressure: Decimal
    drift_score: Decimal
    recommendations: list[str]


class AutonomyStatusResponse(BaseModel):
    safety_level: str
    emergency_stop_active: bool
    enterprise_ops_enabled: bool
    autonomy_enabled: bool
    pending_journal_entries: int
    recommendations: list[str]


class RemediationHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action_type: str
    status: str
    dry_run: bool
    detail: str
    decision_id: str
    created_at: datetime


class PaginatedRemediationHistoryResponse(BaseModel):
    items: list[RemediationHistoryItem]
    total: int
    skip: int
    limit: int


class SimulationRequest(BaseModel):
    scenario: str = Field(default="full_cycle", description="full_cycle | forecast_only")


class SimulationResponse(BaseModel):
    dry_run: bool
    forecast: OperationalForecastResponse
    executed_steps: int
    blocked_steps: int
    detail: str


class SchedulePolicyResponse(BaseModel):
    maintenance_windows: dict | None
    blackout_periods: dict | None
    fairness_weight: float | None
    rebuild_priority_bias: float | None
    adaptive_rebuild_enabled: bool
    in_blackout: bool
