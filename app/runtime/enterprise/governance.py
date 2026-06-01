"""Autonomous governance — permission matrix, safety levels, emergency stop."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.runtime.enterprise.dto import AutonomySafetyLevel, OperationalDecisionKind
from app.runtime.reliability.kill_switches import KillSwitchDomain, RuntimeKillSwitches


@dataclass(frozen=True)
class AutonomyPermissionResult:
    allowed: bool
    requires_approval: bool
    blocked_reason: str | None


class AutonomyPermissionMatrix:
    """Policy-governed autonomy boundaries."""

    ALLOWED_BY_LEVEL: dict[AutonomySafetyLevel, frozenset[OperationalDecisionKind]] = {
        AutonomySafetyLevel.OFF: frozenset(),
        AutonomySafetyLevel.MONITOR: frozenset({OperationalDecisionKind.NO_ACTION}),
        AutonomySafetyLevel.LIMITED: frozenset(
            {
                OperationalDecisionKind.NO_ACTION,
                OperationalDecisionKind.RESET_STALE_REBUILD,
                OperationalDecisionKind.RECOVER_STUCK_JOBS,
            }
        ),
        AutonomySafetyLevel.STANDARD: frozenset(OperationalDecisionKind),
    }

    APPROVAL_REQUIRED: frozenset[OperationalDecisionKind] = frozenset(
        {OperationalDecisionKind.DEFER_REBUILD, OperationalDecisionKind.THROTTLE_DISPATCH}
    )

    @classmethod
    def safety_level(cls) -> AutonomySafetyLevel:
        raw = getattr(settings, "runtime_autonomy_safety_level", "standard").lower()
        try:
            return AutonomySafetyLevel(raw)
        except ValueError:
            return AutonomySafetyLevel.STANDARD

    @classmethod
    def emergency_stop_active(cls) -> bool:
        autonomy = RuntimeKillSwitches.check(KillSwitchDomain.AUTONOMY)
        return not autonomy.allowed

    @classmethod
    def evaluate(
        cls,
        kind: OperationalDecisionKind,
        *,
        dry_run: bool,
    ) -> AutonomyPermissionResult:
        if cls.emergency_stop_active():
            return AutonomyPermissionResult(
                allowed=dry_run,
                requires_approval=True,
                blocked_reason="RUNTIME_AUTONOMY kill switch active",
            )
        level = cls.safety_level()
        allowed_kinds = cls.ALLOWED_BY_LEVEL.get(level, frozenset())
        if kind not in allowed_kinds:
            return AutonomyPermissionResult(
                allowed=False,
                requires_approval=True,
                blocked_reason=f"action {kind.value} not permitted at safety level {level.value}",
            )
        requires = kind in cls.APPROVAL_REQUIRED and not dry_run
        return AutonomyPermissionResult(
            allowed=True,
            requires_approval=requires,
            blocked_reason=None,
        )
