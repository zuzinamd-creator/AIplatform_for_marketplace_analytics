"""Enterprise operations DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class AutonomySafetyLevel(StrEnum):
    OFF = "off"
    MONITOR = "monitor"
    LIMITED = "limited"
    STANDARD = "standard"


class OperationalDecisionKind(StrEnum):
    HEAL_QUEUE = "heal_queue"
    RESET_STALE_REBUILD = "reset_stale_rebuild"
    DEFER_REBUILD = "defer_rebuild"
    RECOVER_STUCK_JOBS = "recover_stuck_jobs"
    THROTTLE_DISPATCH = "throttle_dispatch"
    NO_ACTION = "no_action"


@dataclass(frozen=True)
class OperationalForecastDTO:
    queue_saturation_score: Decimal
    rebuild_pressure_score: Decimal
    overload_risk: Decimal
    autonomy_health_score: Decimal
    ai_execution_pressure: Decimal
    drift_score: Decimal
    recommendations: tuple[str, ...]


@dataclass(frozen=True)
class OperationalDecisionDTO:
    decision_id: str
    kind: OperationalDecisionKind
    rationale: str
    requires_approval: bool
    reversible: bool
    priority: int


@dataclass(frozen=True)
class RemediationStepDTO:
    step_id: str
    action_type: str
    reversible: bool
    detail: str


@dataclass(frozen=True)
class RemediationPlanDTO:
    plan_id: str
    decisions: tuple[OperationalDecisionDTO, ...]
    steps: tuple[RemediationStepDTO, ...]
    dependency_notes: str = ""


@dataclass(frozen=True)
class RemediationResultDTO:
    plan_id: str
    dry_run: bool
    executed_steps: int
    blocked_steps: int
    detail: str


@dataclass
class EnterpriseOpsCycleResult:
    forecast: OperationalForecastDTO
    plan: RemediationPlanDTO
    remediation: RemediationResultDTO
    journal_ids: list[UUID] = field(default_factory=list)
