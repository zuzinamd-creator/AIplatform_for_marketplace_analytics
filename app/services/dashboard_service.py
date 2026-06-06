"""Single-request dashboard aggregation (parallel server-side fan-out)."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from typing import TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.models.report import Marketplace
from app.models.user import User
from app.schemas.ai_intelligence import (
    AIOperationalStatusResponse,
    PaginatedRecommendationsResponse,
    PriorityQueueItemResponse,
    RecommendationResponse,
    TodaysFocusResponse,
)
from app.schemas.analytics import (
    AnalyticsCoverageResponse,
    CostCoverageResponse,
    FinancialKpiSummaryResponse,
    FinancialTrendsResponse,
    RevenueKpiSummaryResponse,
    RevenueTrendResponse,
    TopSkusResponse,
)
from app.schemas.dashboard import DashboardSummaryResponse
from app.schemas.ops import PaginatedQueueResponse, QueueJobOpsResponse
from app.schemas.ops_runtime import RuntimeSummaryResponse
from app.services.ai_service import AIService
from app.services.analytics_service import AnalyticsService, Period
from app.services.cost_coverage_service import CostCoverageService, CoveragePeriod
from app.services.ops_service import OpsService

T = TypeVar("T")


class DashboardService:
    def __init__(self, db: AsyncSession, user: User) -> None:
        self.db = db
        self.user = user

    async def _run(self, fn) -> T:
        """Each fan-out task gets its own DB session (asyncpg is not concurrent per connection)."""
        async with SessionLocal() as session:
            return await fn(session)

    async def summary(
        self,
        *,
        marketplace: Marketplace,
        start: date,
        end: date,
        compare_start: date | None = None,
        compare_end: date | None = None,
    ) -> DashboardSummaryResponse:
        user = self.user
        user_id: UUID = user.id
        period = Period(start=start, end=end)

        coros: list = [
            self._run(lambda db: OpsService(db, user).list_queue_jobs(skip=0, limit=10)),
            self._run(lambda db: OpsService(db, user).runtime_summary()),
            self._run(lambda db: AIService(db, user_id).operational_status()),
            self._run(lambda db: AIService(db, user_id).todays_focus()),
            self._run(lambda db: AIService(db, user_id).list_recommendations(skip=0, limit=5)),
            self._run(
                lambda db: AnalyticsService(db, user).revenue_summary(marketplace=marketplace, period=period)
            ),
            self._run(
                lambda db: AnalyticsService(db, user).revenue_trend(marketplace=marketplace, period=period)
            ),
            self._run(
                lambda db: AnalyticsService(db, user).financial_summary(marketplace=marketplace, period=period)
            ),
            self._run(
                lambda db: AnalyticsService(db, user).financial_trends(marketplace=marketplace, period=period)
            ),
            self._run(
                lambda db: AnalyticsService(db, user).top_skus(
                    marketplace=marketplace, period=period, limit=5, sort="revenue"
                )
            ),
            self._run(lambda db: AnalyticsService(db, user).coverage()),
            self._run(
                lambda db: CostCoverageService(db, user_id).analyze(
                    marketplace=marketplace,
                    period=CoveragePeriod(start=start, end=end),
                    limit=20,
                )
            ),
        ]
        if compare_start is not None and compare_end is not None:
            compare_period = Period(start=compare_start, end=compare_end)
            coros.append(
                self._run(
                    lambda db: AnalyticsService(db, user).revenue_summary(
                        marketplace=marketplace, period=compare_period
                    )
                )
            )

        results = await asyncio.gather(*coros)

        queue_rows, queue_total, status_counts = results[0]
        runtime = results[1]
        ai_ops_raw = results[2]
        focus_raw = results[3]
        rec_rows, rec_total = results[4]
        revenue = results[5]
        revenue_trend = results[6]
        finance = results[7]
        finance_trend = results[8]
        top_skus = results[9]
        coverage = results[10]
        cost_coverage = results[11]
        revenue_compare = results[12] if len(results) > 12 else None

        return DashboardSummaryResponse(
            queue=PaginatedQueueResponse(
                items=[QueueJobOpsResponse.model_validate(r) for r in queue_rows],
                page=OpsService.page_meta(queue_total, 0, 10),
                status_counts=status_counts,
            ),
            runtime=runtime,
            ai_ops=AIOperationalStatusResponse(
                overall_score=ai_ops_raw.overall_score,
                degraded_intelligence_mode=ai_ops_raw.degraded_intelligence_mode,
                runs_total=ai_ops_raw.runs_total,
                success_rate=ai_ops_raw.success_rate,
                pending_approvals=ai_ops_raw.pending_approvals,
                avg_confidence=ai_ops_raw.avg_confidence,
                recommendations=list(ai_ops_raw.recommendations),
            ),
            todays_focus=TodaysFocusResponse(
                generated_at=focus_raw.generated_at,
                headline=focus_raw.headline,
                requires_attention_today=list(focus_raw.requires_attention_today),
                can_wait=list(focus_raw.can_wait),
                dangerous=list(focus_raw.dangerous),
                highest_upside=list(focus_raw.highest_upside),
                top_actions=list(focus_raw.top_actions),
                critical_alerts=list(focus_raw.critical_alerts),
                quick_wins=list(focus_raw.quick_wins),
                priority_queue=[
                    PriorityQueueItemResponse(
                        recommendation_id=i.recommendation_id,
                        title=i.title,
                        summary=i.summary,
                        recommendation_score=i.recommendation_score,
                        priority_tier=i.priority_tier,
                        priority_score=i.priority_score,
                        seller_usefulness=i.seller_usefulness,
                    )
                    for i in focus_raw.priority_queue
                ],
                advisory_notice=focus_raw.advisory_notice,
            ),
            recommendations=PaginatedRecommendationsResponse(
                items=[RecommendationResponse.model_validate(r) for r in rec_rows],
                page=AIService.page_meta(rec_total, 0, 5),
            ),
            revenue_summary=RevenueKpiSummaryResponse.model_validate(revenue),
            revenue_summary_compare=(
                RevenueKpiSummaryResponse.model_validate(revenue_compare)
                if revenue_compare is not None
                else None
            ),
            revenue_trend_daily=RevenueTrendResponse.model_validate(revenue_trend),
            finance_summary=FinancialKpiSummaryResponse.model_validate(finance),
            finance_trend_daily=FinancialTrendsResponse.model_validate(finance_trend),
            top_skus=TopSkusResponse.model_validate(top_skus),
            coverage=AnalyticsCoverageResponse.model_validate(coverage),
            cost_coverage=CostCoverageResponse.model_validate(cost_coverage),
            generated_at=datetime.now(UTC).isoformat(),
        )
