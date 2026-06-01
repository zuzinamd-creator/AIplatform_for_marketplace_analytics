"""Backward-compatible re-exports; prefer app.runtime.scheduling.registry."""

from app.runtime.scheduling.registry import ScheduleKind, ScheduleTick

__all__ = ["ScheduleKind", "ScheduleTick"]
