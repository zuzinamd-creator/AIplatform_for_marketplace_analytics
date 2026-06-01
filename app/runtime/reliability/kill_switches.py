"""Centralized runtime kill switches — config-driven, observable."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.core.config import settings


class KillSwitchDomain(StrEnum):
    WORKER = "worker"
    ORCHESTRATOR = "orchestrator"
    REBUILD_DISPATCH = "rebuild_dispatch"
    AUTONOMY = "autonomy"
    AI_EXECUTION = "ai_execution"
    MAINTENANCE = "maintenance"


@dataclass(frozen=True)
class KillSwitchDecision:
    allowed: bool
    domain: KillSwitchDomain
    reason: str


class RuntimeKillSwitches:
    @staticmethod
    def check(domain: KillSwitchDomain) -> KillSwitchDecision:
        if settings.maintenance_mode and domain != KillSwitchDomain.MAINTENANCE:
            return KillSwitchDecision(
                allowed=False,
                domain=domain,
                reason="maintenance_mode enabled",
            )
        if domain == KillSwitchDomain.WORKER and not settings.worker_enabled:
            return KillSwitchDecision(False, domain, "worker disabled (WORKER_ENABLED=false)")
        if domain == KillSwitchDomain.ORCHESTRATOR and not settings.orchestrator_enabled:
            return KillSwitchDecision(False, domain, "orchestrator disabled")
        if domain == KillSwitchDomain.REBUILD_DISPATCH and not settings.orchestrator_enabled:
            return KillSwitchDecision(False, domain, "rebuild dispatch disabled")
        if domain == KillSwitchDomain.AUTONOMY and not settings.runtime_autonomy_enabled:
            return KillSwitchDecision(False, domain, "autonomy disabled")
        if domain == KillSwitchDomain.AI_EXECUTION and not settings.ai_enabled:
            return KillSwitchDecision(False, domain, "AI disabled")
        return KillSwitchDecision(True, domain, "ok")

    @staticmethod
    def ai_paused_for_overload(*, queue_pending: int) -> bool:
        if not settings.runtime_ai_pause_when_overloaded:
            return False
        return queue_pending > settings.runtime_queue_overload_threshold
