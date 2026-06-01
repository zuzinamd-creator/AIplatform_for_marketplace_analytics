"""Platform degradation assessment — derived, not persisted."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.runtime.control_plane.state import RuntimeHealthSeverity
from app.runtime.health.evaluator import PlatformHealthReport
from app.runtime.reliability.kill_switches import KillSwitchDomain, RuntimeKillSwitches


class DegradationLevel(StrEnum):
    NORMAL = "normal"
    DEGRADED = "degraded"
    LIMITED = "limited"
    MAINTENANCE = "maintenance"


@dataclass(frozen=True)
class DegradationAssessment:
    level: DegradationLevel
    reason: str
    health_severity: RuntimeHealthSeverity


def assess_platform_degradation(
    *,
    health: PlatformHealthReport,
    queue_pending: int,
) -> DegradationAssessment:
    maintenance = RuntimeKillSwitches.check(KillSwitchDomain.MAINTENANCE)
    if not maintenance.allowed:
        return DegradationAssessment(
            level=DegradationLevel.MAINTENANCE,
            reason=maintenance.reason,
            health_severity=health.overall_severity,
        )
    if health.overall_severity == RuntimeHealthSeverity.CRITICAL:
        return DegradationAssessment(
            level=DegradationLevel.LIMITED,
            reason="critical health — dispatch/AI may be throttled",
            health_severity=health.overall_severity,
        )
    if (
        health.overall_severity == RuntimeHealthSeverity.WARN
        or RuntimeKillSwitches.ai_paused_for_overload(queue_pending=queue_pending)
    ):
        return DegradationAssessment(
            level=DegradationLevel.DEGRADED,
            reason="elevated queue/rebuild pressure",
            health_severity=health.overall_severity,
        )
    return DegradationAssessment(
        level=DegradationLevel.NORMAL,
        reason="nominal",
        health_severity=health.overall_severity,
    )
