"""Operational decision engine — policy-governed remediation choices."""

from __future__ import annotations

from uuid import uuid4

from app.runtime.enterprise.dto import (
    OperationalDecisionDTO,
    OperationalDecisionKind,
    OperationalForecastDTO,
)
from app.runtime.observability import QueueObservabilitySnapshot, RebuildQueueObservabilitySnapshot
from app.runtime.policy.engine import RuntimeOperationalPolicy


class OperationalDecisionEngine:
    def decide(
        self,
        *,
        forecast: OperationalForecastDTO,
        queue: QueueObservabilitySnapshot,
        rebuild: RebuildQueueObservabilitySnapshot,
        policy: RuntimeOperationalPolicy,
        in_blackout: bool,
    ) -> list[OperationalDecisionDTO]:
        if in_blackout:
            return [
                OperationalDecisionDTO(
                    decision_id=str(uuid4()),
                    kind=OperationalDecisionKind.NO_ACTION,
                    rationale="Maintenance blackout active",
                    requires_approval=False,
                    reversible=True,
                    priority=0,
                )
            ]

        decisions: list[OperationalDecisionDTO] = []
        if rebuild.running > policy.max_rebuild_attempts_default:
            decisions.append(
                OperationalDecisionDTO(
                    decision_id=str(uuid4()),
                    kind=OperationalDecisionKind.RESET_STALE_REBUILD,
                    rationale="Elevated RUNNING rebuild count",
                    requires_approval=False,
                    reversible=True,
                    priority=90,
                )
            )
        if queue.pending_count > policy.queue_overload_threshold:
            decisions.append(
                OperationalDecisionDTO(
                    decision_id=str(uuid4()),
                    kind=OperationalDecisionKind.DEFER_REBUILD,
                    rationale="Queue overload — defer non-critical rebuilds",
                    requires_approval=True,
                    reversible=True,
                    priority=80,
                )
            )
            decisions.append(
                OperationalDecisionDTO(
                    decision_id=str(uuid4()),
                    kind=OperationalDecisionKind.HEAL_QUEUE,
                    rationale="Queue saturation — recover stuck jobs sample",
                    requires_approval=False,
                    reversible=True,
                    priority=70,
                )
            )
        elif forecast.overload_risk >= 60:
            decisions.append(
                OperationalDecisionDTO(
                    decision_id=str(uuid4()),
                    kind=OperationalDecisionKind.THROTTLE_DISPATCH,
                    rationale="Predictive overload — throttle dispatch",
                    requires_approval=True,
                    reversible=True,
                    priority=50,
                )
            )
        if queue.processing_count > 0 and forecast.drift_score >= 20:
            decisions.append(
                OperationalDecisionDTO(
                    decision_id=str(uuid4()),
                    kind=OperationalDecisionKind.RECOVER_STUCK_JOBS,
                    rationale="Processing jobs with operational drift",
                    requires_approval=False,
                    reversible=True,
                    priority=60,
                )
            )
        if not decisions:
            decisions.append(
                OperationalDecisionDTO(
                    decision_id=str(uuid4()),
                    kind=OperationalDecisionKind.NO_ACTION,
                    rationale="Platform within policy thresholds",
                    requires_approval=False,
                    reversible=True,
                    priority=0,
                )
            )
        return sorted(decisions, key=lambda d: d.priority, reverse=True)
