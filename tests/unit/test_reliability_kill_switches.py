"""Kill switch and degradation tests."""

from __future__ import annotations

from app.runtime.reliability.degradation import DegradationLevel, assess_platform_degradation
from app.runtime.reliability.kill_switches import KillSwitchDomain, RuntimeKillSwitches


def test_maintenance_mode_blocks_worker() -> None:
    from app.core.config import settings

    original = settings.maintenance_mode
    settings.maintenance_mode = True
    try:
        decision = RuntimeKillSwitches.check(KillSwitchDomain.WORKER)
        assert decision.allowed is False
    finally:
        settings.maintenance_mode = original


def test_degradation_critical_is_limited() -> None:
    from app.runtime.control_plane.state import RuntimeHealthSeverity
    from app.runtime.health.evaluator import HealthDimension, PlatformHealthReport

    report = PlatformHealthReport(
        overall_score=40.0,
        overall_severity=RuntimeHealthSeverity.CRITICAL,
        dimensions=(
            HealthDimension("queue", 40.0, RuntimeHealthSeverity.CRITICAL, "overload"),
        ),
        recommendations=("Review capacity",),
    )
    assessment = assess_platform_degradation(health=report, queue_pending=1000)
    assert assessment.level == DegradationLevel.LIMITED
