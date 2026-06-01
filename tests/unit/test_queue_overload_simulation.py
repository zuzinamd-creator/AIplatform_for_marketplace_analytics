"""Queue overload simulation — dispatch throttling under pressure."""

from __future__ import annotations

from app.runtime.policy.engine import RuntimeOperationalPolicy


def test_policy_throttles_high_queue() -> None:
    policy = RuntimeOperationalPolicy.from_settings()
    assert policy.should_throttle_dispatch(queue_pending=10_000, rebuild_backlog=0) is True
