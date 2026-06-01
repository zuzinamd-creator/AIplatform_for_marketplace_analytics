"""AI digest generation — daily, weekly executive, anomaly summaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security_context import TenantSession
from app.models.ai_intelligence import AIRecommendation, SellerWorkflowState


@dataclass(frozen=True)
class DigestSectionDTO:
    title: str
    body: str
    priority: str


@dataclass(frozen=True)
class AIDigestDTO:
    digest_type: str
    generated_at: datetime
    headline: str
    sections: tuple[DigestSectionDTO, ...]
    active_recommendation_count: int
    advisory_notice: str


class AIDigestService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def generate(self, digest_type: str) -> AIDigestDTO:
        if digest_type == "daily":
            return await self._daily()
        if digest_type == "weekly":
            return await self._weekly()
        if digest_type == "anomaly":
            return await self._anomaly()
        raise ValueError(f"unknown digest_type: {digest_type}")

    async def _active_recommendations(self, *, since: datetime | None = None) -> list[AIRecommendation]:
        async with TenantSession.transaction(self.db, self.user_id):
            q = (
                select(AIRecommendation)
                .where(AIRecommendation.user_id == self.user_id)
                .where(
                    AIRecommendation.seller_workflow_state.in_(
                        (SellerWorkflowState.ACTIVE.value, SellerWorkflowState.SAVED.value)
                    )
                )
                .order_by(AIRecommendation.priority_score.desc().nullslast())
            )
            if since is not None:
                q = q.where(AIRecommendation.created_at >= since)
            rows = (await self.db.execute(q.limit(20))).scalars().all()
        return list(rows)

    async def _daily(self) -> AIDigestDTO:
        since = datetime.now(UTC) - timedelta(days=1)
        rows = await self._active_recommendations(since=since)
        sections: list[DigestSectionDTO] = []
        for r in rows[:5]:
            plan = r.action_plan or {}
            sections.append(
                DigestSectionDTO(
                    title=r.title[:120],
                    body=str(plan.get("why_this_matters") or r.summary)[:400],
                    priority=_priority_band(r.priority_score),
                )
            )
        headline = (
            f"{len(rows)} active recommendation(s) in the last 24h"
            if rows
            else "No new active recommendations in the last 24h"
        )
        return AIDigestDTO(
            digest_type="daily",
            generated_at=datetime.now(UTC),
            headline=headline,
            sections=tuple(sections),
            active_recommendation_count=len(rows),
            advisory_notice=_advisory_notice(),
        )

    async def _weekly(self) -> AIDigestDTO:
        since = datetime.now(UTC) - timedelta(days=7)
        rows = await self._active_recommendations(since=since)
        sections: list[DigestSectionDTO] = []
        if rows:
            top = rows[0]
            plan = top.action_plan or {}
            sections.append(
                DigestSectionDTO(
                    title="Top priority this week",
                    body=str(plan.get("expected_business_impact") or top.summary)[:500],
                    priority="high",
                )
            )
        for r in rows[1:4]:
            sections.append(
                DigestSectionDTO(
                    title=r.title[:100],
                    body=r.summary[:300],
                    priority=_priority_band(r.priority_score),
                )
            )
        headline = f"Weekly executive summary — {len(rows)} open item(s)"
        return AIDigestDTO(
            digest_type="weekly",
            generated_at=datetime.now(UTC),
            headline=headline,
            sections=tuple(sections),
            active_recommendation_count=len(rows),
            advisory_notice=_advisory_notice(),
        )

    async def _anomaly(self) -> AIDigestDTO:
        since = datetime.now(UTC) - timedelta(days=7)
        async with TenantSession.transaction(self.db, self.user_id):
            rows = (
                await self.db.execute(
                    select(AIRecommendation)
                    .where(AIRecommendation.user_id == self.user_id)
                    .where(AIRecommendation.workflow_type.in_(("anomaly_explanation", "risk_detection")))
                    .where(AIRecommendation.created_at >= since)
                    .order_by(AIRecommendation.created_at.desc())
                    .limit(10)
                )
            ).scalars().all()
        sections = [
            DigestSectionDTO(
                title=r.title[:120],
                body=r.summary[:400],
                priority="high"
                if (r.risk_class and getattr(r.risk_class, "value", str(r.risk_class)) in ("high", "critical"))
                else "medium",
            )
            for r in rows
        ]
        headline = f"Anomaly alert summary — {len(rows)} item(s) in 7 days"
        return AIDigestDTO(
            digest_type="anomaly",
            generated_at=datetime.now(UTC),
            headline=headline,
            sections=tuple(sections),
            active_recommendation_count=len(rows),
            advisory_notice=_advisory_notice(),
        )


def _priority_band(score: float | None) -> str:
    if score is None:
        return "medium"
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _advisory_notice() -> str:
    return (
        "All digests are advisory summaries over governed analytics. "
        "Verify evidence on each recommendation before marketplace changes."
    )
