"""Tenant-scoped AI cost reporting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security_context import TenantSession
from app.models.ai_execution import AIExecutionRun


@dataclass(frozen=True)
class CostReportDTO:
    period_start: date | None
    period_end: date | None
    runs_total: int
    estimated_cost_usd: float
    daily_cap_usd: float
    daily_spend_usd: float
    daily_cap_remaining_usd: float
    per_run_cap_usd: float
    by_workflow: list[dict]
    by_prompt: list[dict]
    by_provider: list[dict]
    expensive_runs: list[dict]
    repeated_prompts: list[dict]
    generated_at: datetime


async def build_cost_report(
    db: AsyncSession,
    user_id: UUID,
    *,
    start: date | None = None,
    end: date | None = None,
) -> CostReportDTO:
    async with TenantSession.transaction(db, user_id):
        filters = [AIExecutionRun.user_id == user_id]
        if start is not None:
            filters.append(func.date(AIExecutionRun.created_at) >= start)
        if end is not None:
            filters.append(func.date(AIExecutionRun.created_at) <= end)

        runs_total = (
            await db.execute(select(func.count()).select_from(AIExecutionRun).where(*filters))
        ).scalar_one()
        cost_total = (
            await db.execute(
                select(func.coalesce(func.sum(AIExecutionRun.estimated_cost), 0)).where(*filters)
            )
        ).scalar_one()

        by_workflow = (
            await db.execute(
                select(
                    AIExecutionRun.agent_kind,
                    func.count().label("runs"),
                    func.coalesce(func.sum(AIExecutionRun.estimated_cost), 0).label("cost"),
                )
                .where(*filters)
                .group_by(AIExecutionRun.agent_kind)
                .order_by(func.sum(AIExecutionRun.estimated_cost).desc())
            )
        ).all()

        by_prompt = (
            await db.execute(
                select(
                    AIExecutionRun.prompt_id,
                    func.count().label("runs"),
                    func.coalesce(func.sum(AIExecutionRun.estimated_cost), 0).label("cost"),
                )
                .where(*filters)
                .group_by(AIExecutionRun.prompt_id)
                .order_by(func.count().desc())
                .limit(10)
            )
        ).all()

        by_provider = (
            await db.execute(
                select(
                    AIExecutionRun.provider_name,
                    func.count().label("runs"),
                    func.coalesce(func.sum(AIExecutionRun.estimated_cost), 0).label("cost"),
                )
                .where(*filters)
                .group_by(AIExecutionRun.provider_name)
            )
        ).all()

        expensive = (
            await db.execute(
                select(AIExecutionRun)
                .where(*filters)
                .where(AIExecutionRun.estimated_cost.is_not(None))
                .order_by(AIExecutionRun.estimated_cost.desc())
                .limit(5)
            )
        ).scalars().all()

        repeated = (
            await db.execute(
                select(
                    AIExecutionRun.prompt_id,
                    func.count().label("c"),
                )
                .where(*filters)
                .group_by(AIExecutionRun.prompt_id)
                .having(func.count() > 2)
                .order_by(func.count().desc())
                .limit(5)
            )
        ).all()

        today = datetime.now(UTC).date()
        daily_spend = (
            await db.execute(
                select(func.coalesce(func.sum(AIExecutionRun.estimated_cost), 0)).where(
                    AIExecutionRun.user_id == user_id,
                    func.date(AIExecutionRun.created_at) == today,
                )
            )
        ).scalar_one()

    daily_cap = float(settings.ai_max_cost_per_day_usd)
    daily_spend_f = float(daily_spend or 0)
    return CostReportDTO(
        period_start=start,
        period_end=end,
        runs_total=int(runs_total),
        estimated_cost_usd=float(cost_total or 0),
        daily_cap_usd=daily_cap,
        daily_spend_usd=daily_spend_f,
        daily_cap_remaining_usd=max(0.0, daily_cap - daily_spend_f),
        per_run_cap_usd=float(settings.ai_max_cost_per_run_usd),
        by_workflow=[
            {"workflow": r[0], "runs": int(r[1]), "cost_usd": float(r[2])} for r in by_workflow
        ],
        by_prompt=[{"prompt_id": r[0], "runs": int(r[1]), "cost_usd": float(r[2])} for r in by_prompt],
        by_provider=[
            {"provider": r[0] or "unknown", "runs": int(r[1]), "cost_usd": float(r[2])}
            for r in by_provider
        ],
        expensive_runs=[
            {
                "run_id": str(r.id),
                "cost_usd": float(r.estimated_cost or 0),
                "prompt_id": r.prompt_id,
                "provider": r.provider_name,
            }
            for r in expensive
        ],
        repeated_prompts=[{"prompt_id": r[0], "count": int(r[1])} for r in repeated],
        generated_at=datetime.now(UTC),
    )
