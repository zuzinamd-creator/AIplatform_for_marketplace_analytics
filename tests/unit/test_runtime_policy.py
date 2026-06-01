"""Unit tests for operational policy engine."""

from __future__ import annotations

from app.runtime.policy.engine import RuntimeOperationalPolicy


def test_throttle_when_queue_overloaded() -> None:
    policy = RuntimeOperationalPolicy(
        max_dispatch_per_cycle=1,
        dispatch_batch_size=5,
        queue_overload_threshold=100,
        queue_lag_warn_seconds=300,
        rebuild_runaway_per_hour=30,
        max_rebuild_attempts_default=5,
        defer_busy_seconds=60,
        stale_running_seconds=600,
        staging_cleanup_seconds=3600,
        autonomy_enabled=True,
        max_autonomous_actions_per_cycle=3,
        starvation_idle_cycles=60,
        incremental_to_full_after_attempts=3,
        ai_pause_when_overloaded=True,
    )
    assert policy.should_throttle_dispatch(queue_pending=200, rebuild_backlog=0) is True
    assert policy.should_escalate_to_full(attempt_count=3, current_mode="incremental") is True
    assert policy.should_escalate_to_full(attempt_count=1, current_mode="full") is False
