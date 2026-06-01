"""Unit tests for runtime operational forecasting."""

from __future__ import annotations

from app.runtime.enterprise.forecasting import RuntimeIntelligenceEngine
from app.runtime.health.evaluator import RuntimeHealthEvaluator
from app.runtime.observability import QueueObservabilitySnapshot, RebuildQueueObservabilitySnapshot
from app.runtime.policy.engine import RuntimeOperationalPolicy


def test_forecast_elevates_overload_risk() -> None:
    policy = RuntimeOperationalPolicy.from_settings()
    queue = QueueObservabilitySnapshot(policy.queue_overload_threshold, 1, 0, 500)
    rebuild = RebuildQueueObservabilitySnapshot(100, 10, 5, 2)
    health = RuntimeHealthEvaluator().evaluate(queue=queue, rebuild=rebuild)
    forecast = RuntimeIntelligenceEngine().forecast(
        queue=queue, rebuild=rebuild, health=health, policy=policy
    )
    assert forecast.overload_risk >= 50
    assert len(forecast.recommendations) >= 1
