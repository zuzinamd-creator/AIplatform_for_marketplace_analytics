"""Unit tests for explicit schedule registry."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.runtime.scheduling.registry import ScheduleKind, ScheduleRegistry, ScheduleTick


def test_schedule_tick_due_and_advance() -> None:
    past = datetime.now(UTC) - timedelta(seconds=10)
    tick = ScheduleTick(kind=ScheduleKind.HEALTH_EVALUATION, due_at=past, interval_seconds=30.0)
    assert tick.is_due() is True
    advanced = tick.next()
    assert advanced.is_due() is False


def test_registry_default_has_core_kinds() -> None:
    reg = ScheduleRegistry.default()
    assert ScheduleKind.ORCHESTRATION_MAINTENANCE in reg.ticks
    assert ScheduleKind.AUTONOMY_HEALING in reg.ticks
