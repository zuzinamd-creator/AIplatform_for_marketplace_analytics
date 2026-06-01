"""Unit tests for enterprise operational decision engine."""

from __future__ import annotations

from decimal import Decimal

from app.runtime.enterprise.decision_engine import OperationalDecisionEngine
from app.runtime.enterprise.dto import OperationalDecisionKind, OperationalForecastDTO
from app.runtime.enterprise.scheduling import is_in_blackout
from app.runtime.observability import QueueObservabilitySnapshot, RebuildQueueObservabilitySnapshot
from app.runtime.policy.engine import RuntimeOperationalPolicy


def _forecast(
    *,
    overload_risk: Decimal = Decimal("10"),
) -> OperationalForecastDTO:
    return OperationalForecastDTO(
        queue_saturation_score=Decimal("10"),
        rebuild_pressure_score=Decimal("10"),
        overload_risk=overload_risk,
        autonomy_health_score=Decimal("90"),
        ai_execution_pressure=Decimal("0"),
        drift_score=Decimal("0"),
        recommendations=(),
    )


def test_blackout_yields_no_action() -> None:
    decisions = OperationalDecisionEngine().decide(
        forecast=_forecast(),
        queue=QueueObservabilitySnapshot(0, 0, 0, None),
        rebuild=RebuildQueueObservabilitySnapshot(0, 0, 0, 0),
        policy=RuntimeOperationalPolicy.from_settings(),
        in_blackout=True,
    )
    assert decisions[0].kind == OperationalDecisionKind.NO_ACTION


def test_queue_overload_defers_rebuild() -> None:
    policy = RuntimeOperationalPolicy.from_settings()
    decisions = OperationalDecisionEngine().decide(
        forecast=_forecast(overload_risk=Decimal("80")),
        queue=QueueObservabilitySnapshot(
            policy.queue_overload_threshold + 10, 2, 0, 100
        ),
        rebuild=RebuildQueueObservabilitySnapshot(5, 0, 10, 0),
        policy=policy,
        in_blackout=False,
    )
    kinds = {d.kind for d in decisions}
    assert OperationalDecisionKind.DEFER_REBUILD in kinds


def test_is_in_blackout_hour() -> None:
    assert is_in_blackout(blackout_periods=[{"start_hour": 0, "end_hour": 24}]) is True
