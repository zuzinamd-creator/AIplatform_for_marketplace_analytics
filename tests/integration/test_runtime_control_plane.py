"""Integration tests for control plane schedules and autonomy audit."""

from __future__ import annotations

import pytest
from app.models.user import User
from app.runtime.autonomy.audit import record_autonomy_event
from app.runtime.policy.engine import RuntimeOperationalPolicy
from app.runtime.scheduling.executor import ScheduleExecutor
from app.runtime.scheduling.registry import ScheduleKind
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.integration
async def test_record_autonomy_event_tenant_scoped(
    db_session: AsyncSession,
    integration_user: User,
) -> None:
    event_id = await record_autonomy_event(
        db_session,
        action_type="test_autonomy",
        detail="integration autonomy audit",
        user_id=integration_user.id,
        payload={"test": True},
    )
    assert event_id is not None


@pytest.mark.integration
async def test_schedule_executor_autonomy_disabled(db_session: AsyncSession) -> None:
    policy = RuntimeOperationalPolicy(
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
    report = await ScheduleExecutor(db_session, policy=policy).run(ScheduleKind.AUTONOMY_HEALING)
    assert "disabled" in report.detail
