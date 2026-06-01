"""Usefulness analytics — acceptance, fatigue, conversion (read-only aggregates)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security_context import TenantSession
from app.models.ai_intelligence import (
    AIRecommendation,
    AIRecommendationFeedback,
    SellerWorkflowState,
)


@dataclass(frozen=True)
class UsefulnessMetricsDTO:
    total_recommendations: int
    accepted_count: int
    rejected_count: int
    ignored_count: int
    completed_count: int
    dismissed_count: int
    saved_count: int
    snoozed_count: int
    repeated_fingerprint_count: int
    fatigue_top_fingerprints: list[dict]
    action_conversion_rate: float | None
    helpful_rate: float | None
    usefulness_score: float | None
    repeated_dismissals: int
    feedback_trend: str


async def compute_usefulness_metrics(db: AsyncSession, user_id: UUID) -> UsefulnessMetricsDTO:
    async with TenantSession.transaction(db, user_id):
        total = (
            await db.execute(
                select(func.count()).select_from(AIRecommendation).where(AIRecommendation.user_id == user_id)
            )
        ).scalar_one()

        fb = AIRecommendationFeedback
        accepted = (
            await db.execute(
                select(func.count()).where(fb.user_id == user_id).where(fb.feedback_type == "accept")
            )
        ).scalar_one()
        rejected = (
            await db.execute(
                select(func.count()).where(fb.user_id == user_id).where(fb.feedback_type == "reject")
            )
        ).scalar_one()

        cutoff = datetime.now(UTC) - timedelta(days=7)
        with_feedback = select(AIRecommendationFeedback.recommendation_id).where(
            AIRecommendationFeedback.user_id == user_id
        )
        ignored = (
            await db.execute(
                select(func.count())
                .select_from(AIRecommendation)
                .where(AIRecommendation.user_id == user_id)
                .where(AIRecommendation.created_at <= cutoff)
                .where(AIRecommendation.seller_workflow_state == SellerWorkflowState.ACTIVE.value)
                .where(~AIRecommendation.id.in_(with_feedback))
            )
        ).scalar_one()

        completed = (
            await db.execute(
                select(func.count())
                .select_from(AIRecommendation)
                .where(AIRecommendation.user_id == user_id)
                .where(AIRecommendation.seller_workflow_state == SellerWorkflowState.COMPLETED.value)
            )
        ).scalar_one()
        dismissed = (
            await db.execute(
                select(func.count())
                .select_from(AIRecommendation)
                .where(AIRecommendation.user_id == user_id)
                .where(AIRecommendation.seller_workflow_state == SellerWorkflowState.DISMISSED.value)
            )
        ).scalar_one()
        saved = (
            await db.execute(
                select(func.count())
                .select_from(AIRecommendation)
                .where(AIRecommendation.user_id == user_id)
                .where(AIRecommendation.seller_workflow_state == SellerWorkflowState.SAVED.value)
            )
        ).scalar_one()
        snoozed = (
            await db.execute(
                select(func.count())
                .select_from(AIRecommendation)
                .where(AIRecommendation.user_id == user_id)
                .where(AIRecommendation.seller_workflow_state == SellerWorkflowState.SNOOZED.value)
            )
        ).scalar_one()

        fp = AIRecommendation.lineage["fingerprint"].astext  # type: ignore[attr-defined]
        top_fp = (
            await db.execute(
                select(fp.label("fingerprint"), func.count().label("c"))
                .where(AIRecommendation.user_id == user_id)
                .where(fp.is_not(None))
                .group_by(fp)
                .having(func.count() > 1)
                .order_by(func.count().desc())
                .limit(5)
            )
        ).all()
        repeated = sum(int(r[1]) for r in top_fp)

        helpful_rate = (
            await db.execute(
                select(func.avg(case((fb.helpful.is_(True), 1), else_=0))).where(fb.user_id == user_id).where(
                    fb.helpful.is_not(None)
                )
            )
        ).scalar_one_or_none()

        dismiss_count = int(dismissed)
        total_fb = int(accepted) + int(rejected) + dismiss_count
        usefulness_score = None
        if total_fb > 0:
            usefulness_score = round(
                (int(accepted) + int(completed) * 1.2) / max(1, total_fb + int(ignored)) * 100.0,
                2,
            )
        trend = "stable"
        if helpful_rate is not None and float(helpful_rate) >= 0.7:
            trend = "improving"
        elif helpful_rate is not None and float(helpful_rate) < 0.4:
            trend = "needs_attention"

    acted = int(accepted) + int(completed)
    denom = int(total) if int(total) > 0 else 0
    conversion = (acted / denom) if denom else None

    return UsefulnessMetricsDTO(
        total_recommendations=int(total),
        accepted_count=int(accepted),
        rejected_count=int(rejected),
        ignored_count=int(ignored),
        completed_count=int(completed),
        dismissed_count=int(dismissed),
        saved_count=int(saved),
        snoozed_count=int(snoozed),
        repeated_fingerprint_count=int(repeated),
        fatigue_top_fingerprints=[{"fingerprint": r[0], "count": int(r[1])} for r in top_fp],
        action_conversion_rate=conversion,
        helpful_rate=float(helpful_rate) if helpful_rate is not None else None,
        usefulness_score=usefulness_score,
        repeated_dismissals=dismiss_count,
        feedback_trend=trend,
    )
