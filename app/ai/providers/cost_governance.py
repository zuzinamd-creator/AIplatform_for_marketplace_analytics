"""Per-tenant cost caps (advisory runtime — blocks expensive runs)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.policy import AIPolicyViolation
from app.core.config import settings
from app.core.security_context import TenantSession
from app.models.ai_execution import AIExecutionRun


async def assert_daily_cost_allowed(db: AsyncSession, user_id: UUID) -> None:
    if not settings.ai_enable_cost_tracking:
        return
    cap = float(settings.ai_max_cost_per_day_usd)
    if cap <= 0:
        return
    async with TenantSession.transaction(db, user_id):
        today = datetime.now(UTC).date()
        total = (
            await db.execute(
                select(func.coalesce(func.sum(AIExecutionRun.estimated_cost), 0))
                .where(AIExecutionRun.user_id == user_id)
                .where(func.date(AIExecutionRun.created_at) == today)
            )
        ).scalar_one()
    if float(total or 0) >= cap:
        raise AIPolicyViolation(
            f"daily AI cost cap reached ({cap} USD). Advisory runs paused until tomorrow."
        )


def assert_run_cost_allowed(estimated_cost_usd: float | None) -> None:
    if not settings.ai_enable_cost_tracking:
        return
    cap = float(settings.ai_max_cost_per_run_usd)
    if cap <= 0 or estimated_cost_usd is None:
        return
    if estimated_cost_usd > cap:
        raise AIPolicyViolation(
            f"estimated run cost {estimated_cost_usd:.4f} USD exceeds cap {cap} USD"
        )
