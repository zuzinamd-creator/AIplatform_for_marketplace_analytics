"""Recommendation fatigue reduction — novelty, cooldown, decay."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security_context import TenantSession
from app.models.ai_intelligence import AIRecommendation

COOLDOWN_DAYS = 3
DECAY_PER_REPEAT = 12.0
SUPPRESS_AFTER_REPEATS = 4


@dataclass(frozen=True)
class FatigueAssessment:
    fingerprint: str
    repeat_count_7d: int
    repeat_count_30d: int
    novelty_score: float
    fatigue_penalty: float
    cooldown_active: bool
    should_suppress_duplicate: bool
    decay_applied: bool


async def assess_fatigue(
    db: AsyncSession,
    user_id: UUID,
    fingerprint: str,
) -> FatigueAssessment:
    now = datetime.now(UTC)
    cutoff_7 = now - timedelta(days=7)
    cutoff_30 = now - timedelta(days=30)
    fp_col = AIRecommendation.lineage["fingerprint"].astext  # type: ignore[attr-defined]

    async with TenantSession.transaction(db, user_id):
        count_7 = (
            await db.execute(
                select(func.count())
                .select_from(AIRecommendation)
                .where(AIRecommendation.user_id == user_id)
                .where(fp_col == fingerprint)
                .where(AIRecommendation.created_at >= cutoff_7)
            )
        ).scalar_one()
        count_30 = (
            await db.execute(
                select(func.count())
                .select_from(AIRecommendation)
                .where(AIRecommendation.user_id == user_id)
                .where(fp_col == fingerprint)
                .where(AIRecommendation.created_at >= cutoff_30)
            )
        ).scalar_one()
        recent = (
            await db.execute(
                select(AIRecommendation.created_at)
                .where(AIRecommendation.user_id == user_id)
                .where(fp_col == fingerprint)
                .order_by(AIRecommendation.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    c7 = int(count_7)
    c30 = int(count_30)
    cooldown = False
    if recent is not None and (now - recent).days < COOLDOWN_DAYS and c7 >= 1:
        cooldown = True

    novelty = max(0.15, 1.0 - (c7 * 0.2) - (c30 * 0.05))
    penalty = min(40.0, c7 * DECAY_PER_REPEAT)
    suppress = c7 >= 1 or (cooldown and c7 >= 1)

    return FatigueAssessment(
        fingerprint=fingerprint,
        repeat_count_7d=c7,
        repeat_count_30d=c30,
        novelty_score=round(novelty, 3),
        fatigue_penalty=penalty,
        cooldown_active=cooldown,
        should_suppress_duplicate=suppress,
        decay_applied=c7 > 0,
    )
