"""Autonomy safety — bounded actions and policy gates."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from app.runtime.autonomy.healer import AutonomousHealer, AutonomyAction
from app.runtime.policy.engine import RuntimeOperationalPolicy


def _disabled_policy() -> RuntimeOperationalPolicy:
    return RuntimeOperationalPolicy(
        max_dispatch_per_cycle=1,
        dispatch_batch_size=5,
        queue_overload_threshold=500,
        queue_lag_warn_seconds=300,
        rebuild_runaway_per_hour=30,
        max_rebuild_attempts_default=5,
        defer_busy_seconds=60,
        stale_running_seconds=600,
        staging_cleanup_seconds=3600,
        autonomy_enabled=False,
        max_autonomous_actions_per_cycle=3,
        starvation_idle_cycles=60,
        incremental_to_full_after_attempts=3,
        ai_pause_when_overloaded=True,
    )


def _enabled_policy(*, cap: int = 1) -> RuntimeOperationalPolicy:
    return RuntimeOperationalPolicy(
        max_dispatch_per_cycle=1,
        dispatch_batch_size=5,
        queue_overload_threshold=500,
        queue_lag_warn_seconds=300,
        rebuild_runaway_per_hour=30,
        max_rebuild_attempts_default=5,
        defer_busy_seconds=60,
        stale_running_seconds=600,
        staging_cleanup_seconds=3600,
        autonomy_enabled=True,
        max_autonomous_actions_per_cycle=cap,
        starvation_idle_cycles=60,
        incremental_to_full_after_attempts=3,
        ai_pause_when_overloaded=True,
    )


@pytest.mark.asyncio
async def test_autonomy_disabled_returns_empty_without_side_effects() -> None:
    healer = AutonomousHealer(AsyncMock(), policy=_disabled_policy())
    assert await healer.run_bounded_cycle() == []


@pytest.mark.asyncio
async def test_autonomy_respects_action_cap() -> None:
    healer = AutonomousHealer(AsyncMock(), policy=_enabled_policy(cap=1))
    healer._reset_stale_rebuilds = AsyncMock(  # type: ignore[method-assign]
        return_value=AutonomyAction("auto_reset_stale_rebuilds", 1, "a")
    )
    healer._defer_overloaded_tenants = AsyncMock(  # type: ignore[method-assign]
        return_value=AutonomyAction("auto_defer_overloaded_tenant", 1, "b")
    )
    healer._recover_stuck_jobs_sample = AsyncMock(  # type: ignore[method-assign]
        return_value=AutonomyAction("auto_recover_stuck_jobs", 1, "c")
    )
    actions = await healer.run_bounded_cycle()
    assert len(actions) == 1
