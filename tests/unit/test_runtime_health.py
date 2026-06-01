"""Unit tests for runtime health evaluation."""

from __future__ import annotations

from app.runtime.control_plane.state import RuntimeHealthSeverity
from app.runtime.health.evaluator import RuntimeHealthEvaluator
from app.runtime.observability import QueueObservabilitySnapshot, RebuildQueueObservabilitySnapshot


def test_health_nominal_scores_ok() -> None:
    report = RuntimeHealthEvaluator().evaluate(
        queue=QueueObservabilitySnapshot(1, 0, 0, 10),
        rebuild=RebuildQueueObservabilitySnapshot(0, 0, 0, 0),
    )
    assert report.overall_severity == RuntimeHealthSeverity.OK
    assert report.overall_score >= 90.0


def test_health_queue_overload_critical() -> None:
    report = RuntimeHealthEvaluator().evaluate(
        queue=QueueObservabilitySnapshot(10_000, 0, 0, None),
        rebuild=RebuildQueueObservabilitySnapshot(0, 0, 0, 0),
    )
    assert report.overall_severity == RuntimeHealthSeverity.CRITICAL
    assert any(d.name == "queue" for d in report.dimensions)
