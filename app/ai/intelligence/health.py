"""AI operational health and quality assessment."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security_context import TenantSession
from app.models.ai_execution import AIExecutionRun, AIExecutionStatus
from app.models.ai_intelligence import AIRecommendation, RecommendationStatus


@dataclass(frozen=True)
class AIOperationalHealthReport:
    overall_score: float
    degraded_intelligence_mode: bool
    runs_total: int
    success_rate: float
    pending_approvals: int
    avg_confidence: float | None
    recommendations: tuple[str, ...]


class AIOperationalIntelligence:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def assess(self) -> AIOperationalHealthReport:
        async with TenantSession.transaction(self.db, self.user_id):
            total_runs = (
                await self.db.execute(
                    select(func.count())
                    .select_from(AIExecutionRun)
                    .where(AIExecutionRun.user_id == self.user_id)
                )
            ).scalar_one()
            succeeded = (
                await self.db.execute(
                    select(func.count())
                    .select_from(AIExecutionRun)
                    .where(
                        AIExecutionRun.user_id == self.user_id,
                        AIExecutionRun.status == AIExecutionStatus.SUCCEEDED,
                    )
                )
            ).scalar_one()
            pending = (
                await self.db.execute(
                    select(func.count())
                    .select_from(AIRecommendation)
                    .where(
                        AIRecommendation.user_id == self.user_id,
                        AIRecommendation.status == RecommendationStatus.PENDING_APPROVAL,
                    )
                )
            ).scalar_one()
            avg_conf = (
                await self.db.execute(
                    select(func.avg(AIRecommendation.confidence_score)).where(
                        AIRecommendation.user_id == self.user_id
                    )
                )
            ).scalar_one()

        success_rate = float(succeeded) / max(1, int(total_runs))
        score = 100.0 * success_rate
        if int(pending) > 5:
            score -= 15.0
        degraded = success_rate < 0.7 or int(pending) > 10

        recs: list[str] = []
        if degraded:
            recs.append("Review failed AI runs and pending recommendation approvals.")
        if avg_conf is not None and float(avg_conf) < 0.6:
            recs.append("Average recommendation confidence is low — verify grounding data.")

        return AIOperationalHealthReport(
            overall_score=max(0.0, score),
            degraded_intelligence_mode=degraded,
            runs_total=int(total_runs),
            success_rate=success_rate,
            pending_approvals=int(pending),
            avg_confidence=float(avg_conf) if avg_conf is not None else None,
            recommendations=tuple(recs),
        )
