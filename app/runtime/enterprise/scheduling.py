"""Enterprise scheduling — maintenance windows and blackout periods."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security_context import DispatchSession
from app.models.enterprise_runtime import RuntimeSchedulePolicy


def is_in_blackout(
    *,
    now: datetime | None = None,
    blackout_periods: list[dict[str, Any]] | None,
) -> bool:
    """Return True when current UTC time falls in a configured blackout."""
    if not blackout_periods:
        return False
    now = now or datetime.now(UTC)
    hour = now.hour
    for period in blackout_periods:
        start = int(period.get("start_hour", -1))
        end = int(period.get("end_hour", -1))
        if start <= hour < end:
            return True
    return False


class EnterpriseScheduleRegistry:
    """Governed schedule policies with platform-wide blackout defaults."""

    DEFAULT_BLACKOUT: list[dict[str, Any]] = [{"start_hour": 2, "end_hour": 4, "reason": "nightly"}]

    @classmethod
    async def platform_in_blackout(cls, db: AsyncSession) -> bool:
        async with DispatchSession.transaction(db):
            rows = (
                await db.execute(select(RuntimeSchedulePolicy.blackout_periods).limit(1))
            ).first()
        periods = rows[0] if rows and rows[0] else cls.DEFAULT_BLACKOUT
        if isinstance(periods, dict):
            periods = periods.get("periods", cls.DEFAULT_BLACKOUT)
        return is_in_blackout(blackout_periods=list(periods) if periods else None)
