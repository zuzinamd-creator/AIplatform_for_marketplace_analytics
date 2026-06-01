"""Config-driven operational policies (observable, no hidden automation)."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class RuntimeOperationalPolicy:
    max_dispatch_per_cycle: int
    dispatch_batch_size: int
    queue_overload_threshold: int
    queue_lag_warn_seconds: int
    rebuild_runaway_per_hour: int
    max_rebuild_attempts_default: int
    defer_busy_seconds: int
    stale_running_seconds: int
    staging_cleanup_seconds: int
    autonomy_enabled: bool
    max_autonomous_actions_per_cycle: int
    starvation_idle_cycles: int
    incremental_to_full_after_attempts: int
    ai_pause_when_overloaded: bool

    @classmethod
    def from_settings(cls) -> RuntimeOperationalPolicy:
        return cls(
            max_dispatch_per_cycle=settings.orchestrator_max_dispatch_per_cycle,
            dispatch_batch_size=settings.orchestrator_dispatch_batch_size,
            queue_overload_threshold=settings.runtime_queue_overload_threshold,
            queue_lag_warn_seconds=settings.ops_queue_lag_warn_seconds,
            rebuild_runaway_per_hour=settings.orchestrator_runaway_rebuilds_per_hour,
            max_rebuild_attempts_default=5,
            defer_busy_seconds=settings.orchestrator_defer_busy_seconds,
            stale_running_seconds=settings.recovery_stale_running_seconds,
            staging_cleanup_seconds=settings.recovery_staging_older_than_seconds,
            autonomy_enabled=settings.runtime_autonomy_enabled,
            max_autonomous_actions_per_cycle=settings.runtime_max_autonomous_actions_per_cycle,
            starvation_idle_cycles=settings.runtime_starvation_idle_cycles,
            incremental_to_full_after_attempts=settings.runtime_incremental_to_full_after_attempts,
            ai_pause_when_overloaded=settings.runtime_ai_pause_when_overloaded,
        )

    def should_throttle_dispatch(self, *, queue_pending: int, rebuild_backlog: int) -> bool:
        if queue_pending > self.queue_overload_threshold:
            return True
        return rebuild_backlog > self.dispatch_batch_size * 10

    def should_escalate_to_full(self, *, attempt_count: int, current_mode: str) -> bool:
        if current_mode == "full":
            return False
        return attempt_count >= self.incremental_to_full_after_attempts
