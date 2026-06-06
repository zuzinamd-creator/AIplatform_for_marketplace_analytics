"""AI analytics service (tenant-scoped, RLS-enforced)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.analytics.engine import AIAnalyticsEngine
from app.core.security_context import TenantSession
from app.domain.analytics.processor import AnalyticsProcessor
from app.domain.analytics.profit_trust import (
    apply_profit_trust_to_ai_metrics,
    apply_profit_trust_to_kpis,
    classify_profit_trust,
)
from app.dto.ai_analytics_dto import AIRunRequestDTO, ValidatedInsightDTO
from app.dto.analytics_dto import AIInsightInputDTO, AnomalyDTO, TopSKUSummaryDTO
from app.models.ai_execution import AIExecutionRun
from app.models.ai_insights import AIInsight
from app.models.ai_intelligence import AIRecommendation, AIRecommendationFeedback
from app.models.finance.aggregates import DailyAggregate, SkuDailyMetric
from app.models.report import Marketplace, Report
from app.models.workflow import SellerWorkflowEvent
from app.schemas.ai import PageMeta
from app.schemas.ai_intelligence import RecommendationStatsResponse
from app.schemas.ai_usage import AIUsageResponse
from app.services.cost_coverage_service import CostCoverageService, CoveragePeriod
from app.services.reconciliation_service import ReconciliationPeriod, ReconciliationService


class AIService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def create_run(
        self, request: AIRunRequestDTO
    ) -> tuple[AIExecutionRun, ValidatedInsightDTO, UUID | None]:
        insight_input = await self._insight_input_for_report(request.report_id)
        engine = AIAnalyticsEngine(self.db, self.user_id)
        return await engine.execute(request, insight_input=insight_input)

    async def create_run_stream(self, request: AIRunRequestDTO):
        insight_input = await self._insight_input_for_report(request.report_id)
        engine = AIAnalyticsEngine(self.db, self.user_id)
        async for evt in engine.execute_stream(request, insight_input=insight_input):
            yield evt

    async def run_intelligence(self, request: AIRunRequestDTO):
        from app.ai.intelligence.engine import AIIntelligenceEngine

        insight_input = await self._insight_input_for_report(request.report_id)
        engine = AIIntelligenceEngine(self.db, self.user_id)
        return await engine.run_intelligence(request, insight_input=insight_input)

    async def run_intelligence_for_period(
        self,
        request: AIRunRequestDTO,
        *,
        marketplace: Marketplace,
        period_start: date,
        period_end: date,
    ):
        from app.ai.intelligence.engine import AIIntelligenceEngine

        insight_input = await self._insight_input_for_period(
            marketplace=marketplace, period_start=period_start, period_end=period_end
        )
        engine = AIIntelligenceEngine(self.db, self.user_id)
        return await engine.run_intelligence(request, insight_input=insight_input)

    async def get_recommendation(self, recommendation_id: UUID) -> AIRecommendation | None:
        async with TenantSession.transaction(self.db, self.user_id):
            return await self.db.get(AIRecommendation, recommendation_id)

    async def list_recommendations(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        seller_state: str | None = None,
        group: str | None = None,
    ) -> tuple[list[AIRecommendation], int]:
        from app.models.ai_intelligence import SellerWorkflowState

        async with TenantSession.transaction(self.db, self.user_id):
            await self._reactivate_expired_snoozes()
            filters = [AIRecommendation.user_id == self.user_id]
            if seller_state:
                filters.append(AIRecommendation.seller_workflow_state == seller_state)
            elif group == "inbox":
                filters.append(
                    AIRecommendation.seller_workflow_state.in_(
                        (SellerWorkflowState.ACTIVE.value, SellerWorkflowState.SAVED.value)
                    )
                )
            total = (
                await self.db.execute(
                    select(func.count()).select_from(AIRecommendation).where(*filters)
                )
            ).scalar_one()
            order = AIRecommendation.priority_score.desc().nullslast()
            rows = (
                await self.db.execute(
                    select(AIRecommendation)
                    .where(*filters)
                    .order_by(order, AIRecommendation.created_at.desc())
                    .offset(skip)
                    .limit(limit)
                )
            ).scalars().all()
        return list(rows), int(total)

    async def _reactivate_expired_snoozes(self) -> None:
        from app.models.ai_intelligence import SellerWorkflowState

        now = datetime.now(UTC)
        rows = (
            await self.db.execute(
                select(AIRecommendation)
                .where(AIRecommendation.user_id == self.user_id)
                .where(AIRecommendation.seller_workflow_state == SellerWorkflowState.SNOOZED.value)
                .where(AIRecommendation.snoozed_until.is_not(None))
                .where(AIRecommendation.snoozed_until <= now)
            )
        ).scalars().all()
        for r in rows:
            r.seller_workflow_state = SellerWorkflowState.ACTIVE.value
            r.snoozed_until = None

    async def update_recommendation_workflow(
        self,
        recommendation_id: UUID,
        *,
        action: str,
        snooze_days: int = 7,
    ) -> AIRecommendation | None:
        from app.models.ai_intelligence import SellerWorkflowState

        async with TenantSession.transaction(self.db, self.user_id):
            row = await self.db.get(AIRecommendation, recommendation_id)
            if row is None or row.user_id != self.user_id:
                return None
            if action == "complete":
                row.seller_workflow_state = SellerWorkflowState.COMPLETED.value
                row.snoozed_until = None
            elif action == "dismiss":
                row.seller_workflow_state = SellerWorkflowState.DISMISSED.value
                row.snoozed_until = None
            elif action == "save":
                row.seller_workflow_state = SellerWorkflowState.SAVED.value
            elif action == "snooze":
                row.seller_workflow_state = SellerWorkflowState.SNOOZED.value
                row.snoozed_until = datetime.now(UTC) + timedelta(days=snooze_days)
            elif action == "reactivate":
                row.seller_workflow_state = SellerWorkflowState.ACTIVE.value
                row.snoozed_until = None
            elif action in ("done_today", "return_later", "waiting_for_data"):
                # Additive tags persisted as events; recommendation state unchanged.
                row.seller_workflow_state = SellerWorkflowState.ACTIVE.value
            else:
                raise ValueError(f"unknown workflow action: {action}")

            self.db.add(
                SellerWorkflowEvent(
                    id=uuid.uuid4(),
                    user_id=self.user_id,
                    recommendation_id=recommendation_id,
                    event_type=f"recommendation.{action}",
                    note=None,
                    reminder_at=row.snoozed_until if action == "snooze" else None,
                    metadata_json={"snooze_days": snooze_days} if action == "snooze" else None,
                )
            )
            await self.db.flush()
            return row

    async def ask_recommendation(self, recommendation_id: UUID, *, question: str):
        from app.ai.product.conversation import answer_follow_up

        row = await self.get_recommendation(recommendation_id)
        if row is None:
            return None
        return answer_follow_up(row, question=question)

    async def generate_digest(self, digest_type: str):
        from app.ai.product.digest import AIDigestService

        return await AIDigestService(self.db, self.user_id).generate(digest_type)

    async def todays_focus(self):
        from app.ai.product.seller_intelligence import TodaysFocusService

        return await TodaysFocusService(self.db, self.user_id).build()

    async def usefulness_metrics(self):
        from app.ai.product.usefulness_metrics import compute_usefulness_metrics

        return await compute_usefulness_metrics(self.db, self.user_id)

    async def recommendation_stats(self) -> RecommendationStatsResponse:
        """Read-only aggregate of recommendation usefulness and fatigue signals."""
        from app.ai.product.usefulness_metrics import compute_usefulness_metrics
        from app.models.ai_intelligence import SellerWorkflowState

        async with TenantSession.transaction(self.db, self.user_id):
            total = (
                await self.db.execute(
                    select(func.count()).select_from(AIRecommendation).where(AIRecommendation.user_id == self.user_id)
                )
            ).scalar_one()

            cutoff = datetime.utcnow() - timedelta(days=7)
            ignored_7d = (
                await self.db.execute(
                    select(func.count())
                    .select_from(AIRecommendation)
                    .where(AIRecommendation.user_id == self.user_id)
                    .where(AIRecommendation.created_at <= cutoff)
                    .where(
                        ~AIRecommendation.id.in_(
                            select(AIRecommendationFeedback.recommendation_id).where(
                                AIRecommendationFeedback.user_id == self.user_id
                            )
                        )
                    )
                )
            ).scalar_one()

            fb = AIRecommendationFeedback
            avg_rating = (
                await self.db.execute(
                    select(func.avg(fb.rating)).where(fb.user_id == self.user_id).where(fb.rating.is_not(None))
                )
            ).scalar_one_or_none()

            helpful_rate = (
                await self.db.execute(
                    select(func.avg(case((fb.helpful.is_(True), 1), else_=0))).where(
                        fb.user_id == self.user_id
                    ).where(fb.helpful.is_not(None))
                )
            ).scalar_one_or_none()

            accept_rate = (
                await self.db.execute(
                    select(func.avg(case((fb.feedback_type == "accept", 1), else_=0))).where(
                        fb.user_id == self.user_id
                    )
                )
            ).scalar_one_or_none()
            reject_rate = (
                await self.db.execute(
                    select(func.avg(case((fb.feedback_type == "reject", 1), else_=0))).where(
                        fb.user_id == self.user_id
                    )
                )
            ).scalar_one_or_none()

            # Fatigue proxy: most frequent fingerprints in recent recommendations.
            fp = AIRecommendation.lineage["fingerprint"].astext  # type: ignore[attr-defined]
            top_fp_rows = (
                await self.db.execute(
                    select(fp.label("fingerprint"), func.count().label("count"))
                    .where(AIRecommendation.user_id == self.user_id)
                    .where(fp.is_not(None))
                    .group_by(fp)
                    .order_by(func.count().desc())
                    .limit(5)
                )
            ).all()

            completed = (
                await self.db.execute(
                    select(func.count())
                    .select_from(AIRecommendation)
                    .where(AIRecommendation.user_id == self.user_id)
                    .where(AIRecommendation.seller_workflow_state == SellerWorkflowState.COMPLETED.value)
                )
            ).scalar_one()
            dismissed = (
                await self.db.execute(
                    select(func.count())
                    .select_from(AIRecommendation)
                    .where(AIRecommendation.user_id == self.user_id)
                    .where(AIRecommendation.seller_workflow_state == SellerWorkflowState.DISMISSED.value)
                )
            ).scalar_one()

        metrics = await compute_usefulness_metrics(self.db, self.user_id)

        return RecommendationStatsResponse(
            total=int(total),
            ignored_7d=int(ignored_7d),
            avg_rating=float(avg_rating) if avg_rating is not None else None,
            helpful_rate=float(helpful_rate) if helpful_rate is not None else None,
            accept_rate=float(accept_rate) if accept_rate is not None else None,
            reject_rate=float(reject_rate) if reject_rate is not None else None,
            fatigue_top_fingerprints=[{"fingerprint": r[0], "count": int(r[1])} for r in top_fp_rows],
            action_conversion_rate=metrics.action_conversion_rate,
            completed_count=int(completed),
            dismissed_count=int(dismissed),
        )

    async def usage(self, *, start: date | None = None, end: date | None = None) -> AIUsageResponse:
        async with TenantSession.transaction(self.db, self.user_id):
            filters = [AIExecutionRun.user_id == self.user_id]
            if start is not None:
                filters.append(func.date(AIExecutionRun.created_at) >= start)
            if end is not None:
                filters.append(func.date(AIExecutionRun.created_at) <= end)

            runs_total = (
                await self.db.execute(
                    select(func.count()).select_from(AIExecutionRun).where(*filters)
                )
            ).scalar_one()

            prompt_tokens, completion_tokens, cost_total = (
                await self.db.execute(
                    select(
                        func.coalesce(func.sum(AIExecutionRun.prompt_tokens), 0),
                        func.coalesce(func.sum(AIExecutionRun.completion_tokens), 0),
                        func.coalesce(func.sum(AIExecutionRun.estimated_cost), 0),
                    ).where(*filters)
                )
            ).one()

            by_provider_rows = (
                await self.db.execute(
                    select(
                        AIExecutionRun.provider_name,
                        func.count().label("runs"),
                        func.coalesce(func.sum(AIExecutionRun.prompt_tokens), 0).label("prompt_tokens"),
                        func.coalesce(func.sum(AIExecutionRun.completion_tokens), 0).label("completion_tokens"),
                        func.coalesce(func.sum(AIExecutionRun.estimated_cost), 0).label("estimated_cost"),
                    )
                    .where(*filters)
                    .group_by(AIExecutionRun.provider_name)
                    .order_by(func.count().desc())
                )
            ).all()

        prompt_tokens_i = int(prompt_tokens or 0)
        completion_tokens_i = int(completion_tokens or 0)
        tokens_total = prompt_tokens_i + completion_tokens_i
        cost = float(cost_total) if cost_total is not None else None

        return AIUsageResponse(
            period_start=start,
            period_end=end,
            runs_total=int(runs_total),
            prompt_tokens=prompt_tokens_i,
            completion_tokens=completion_tokens_i,
            tokens_total=tokens_total,
            estimated_cost_usd=cost,
            by_provider=[
                {
                    "provider_name": r[0] or "unknown",
                    "runs": int(r[1]),
                    "prompt_tokens": int(r[2]),
                    "completion_tokens": int(r[3]),
                    "estimated_cost_usd": float(r[4]) if r[4] is not None else None,
                }
                for r in by_provider_rows
            ],
            generated_at=datetime.now(UTC),
        )

    async def costs_report(self, *, start: date | None = None, end: date | None = None):
        from app.ai.operations.cost_reporting import build_cost_report

        return await build_cost_report(self.db, self.user_id, start=start, end=end)

    async def provider_status(self) -> dict:
        from app.ai.providers.failover import provider_status_payload

        payload = provider_status_payload()
        report = await self.costs_report()
        payload["estimated_monthly_cost_usd"] = round(report.daily_spend_usd * 30.0, 4)
        return payload

    async def record_feedback(
        self,
        recommendation_id: UUID,
        *,
        rating: int | None,
        helpful: bool | None,
        override_reason: str | None,
        feedback_type: str,
    ) -> AIRecommendationFeedback:
        async with TenantSession.transaction(self.db, self.user_id):
            row = AIRecommendationFeedback(
                user_id=self.user_id,
                recommendation_id=recommendation_id,
                rating=rating,
                helpful=helpful,
                override_reason=override_reason,
                feedback_type=feedback_type,
            )
            self.db.add(row)
            await self.db.flush()
            return row

    async def operational_status(self):
        from app.ai.intelligence.health import AIOperationalIntelligence

        return await AIOperationalIntelligence(self.db, self.user_id).assess()

    async def get_run(self, run_id: UUID) -> AIExecutionRun | None:
        async with TenantSession.transaction(self.db, self.user_id):
            return await self.db.get(AIExecutionRun, run_id)

    async def list_runs(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[AIExecutionRun], int]:
        async with TenantSession.transaction(self.db, self.user_id):
            total = (
                await self.db.execute(
                    select(func.count())
                    .select_from(AIExecutionRun)
                    .where(AIExecutionRun.user_id == self.user_id)
                )
            ).scalar_one()
            rows = (
                await self.db.execute(
                    select(AIExecutionRun)
                    .where(AIExecutionRun.user_id == self.user_id)
                    .order_by(AIExecutionRun.created_at.desc())
                    .offset(skip)
                    .limit(limit)
                )
            ).scalars().all()
        return list(rows), int(total)

    async def get_insight(self, insight_id: UUID) -> AIInsight | None:
        async with TenantSession.transaction(self.db, self.user_id):
            return await self.db.get(AIInsight, insight_id)

    async def list_insights(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        workflow: str | None = None,
    ) -> tuple[list[AIInsight], int]:
        async with TenantSession.transaction(self.db, self.user_id):
            filters = [AIInsight.user_id == self.user_id]
            if workflow:
                filters.append(AIInsight.workflow_type == workflow)
            total = (
                await self.db.execute(
                    select(func.count()).select_from(AIInsight).where(*filters)
                )
            ).scalar_one()
            rows = (
                await self.db.execute(
                    select(AIInsight)
                    .where(*filters)
                    .order_by(AIInsight.created_at.desc())
                    .offset(skip)
                    .limit(limit)
                )
            ).scalars().all()
        return list(rows), int(total)

    @staticmethod
    def page_meta(total: int, skip: int, limit: int) -> PageMeta:
        return PageMeta(total=total, skip=skip, limit=limit)

    async def _insight_input_for_report(
        self,
        report_id: UUID | None,
    ) -> AIInsightInputDTO | None:
        async with TenantSession.transaction(self.db, self.user_id):
            report = await self._resolve_report_for_ai(report_id)
            if report is None:
                return None

            marketplace = report.marketplace
            period_bounds = await self.db.execute(
                select(
                    func.min(DailyAggregate.aggregate_date),
                    func.max(DailyAggregate.aggregate_date),
                ).where(
                    DailyAggregate.user_id == self.user_id,
                    DailyAggregate.marketplace == marketplace,
                )
            )
            period_start, period_end = period_bounds.one()
            if period_start is None or period_end is None:
                return AnalyticsProcessor.prepare_ai_insight(
                    report_id=report.id,
                    report_date=report.created_at.date() if report.created_at else date.today(),
                    marketplace_type=marketplace.value,
                    sku_count=0,
                    total_revenue=None,
                    total_profit=None,
                    margin=None,
                    top_skus_summary=[],
                    anomalies=[],
                )

            totals = await self.db.execute(
                select(
                    func.coalesce(func.sum(DailyAggregate.revenue), 0),
                    func.coalesce(func.sum(DailyAggregate.net_profit), 0),
                ).where(
                    DailyAggregate.user_id == self.user_id,
                    DailyAggregate.marketplace == marketplace,
                    DailyAggregate.aggregate_date >= period_start,
                    DailyAggregate.aggregate_date <= period_end,
                )
            )
            total_revenue, total_profit = totals.one()
            total_revenue_d = Decimal(total_revenue)
            total_profit_d = Decimal(total_profit)
            margin = None
            anomalies: list[AnomalyDTO] = []
            if total_revenue_d > 0:
                margin = (total_profit_d / total_revenue_d) * Decimal("100")
                if margin > Decimal("100") or total_profit_d > total_revenue_d * Decimal("2"):
                    anomalies.append(
                        AnomalyDTO(
                            type="data_quality",
                            severity="high",
                            confidence=Decimal("0.9"),
                            message=(
                                "Суммарная прибыль не согласуется с выручкой за период; "
                                "маржу в ответе ИИ не интерпретировать буквально."
                            ),
                        )
                    )
                    margin = None

            top_rows = await self.db.execute(
                select(
                    SkuDailyMetric.sku,
                    func.sum(SkuDailyMetric.revenue).label("revenue"),
                    func.sum(SkuDailyMetric.net_profit).label("net_profit"),
                    func.sum(SkuDailyMetric.units_sold).label("units_sold"),
                )
                .where(
                    SkuDailyMetric.user_id == self.user_id,
                    SkuDailyMetric.marketplace == marketplace,
                    SkuDailyMetric.metric_date >= period_start,
                    SkuDailyMetric.metric_date <= period_end,
                )
                .group_by(SkuDailyMetric.sku)
                .order_by(func.sum(SkuDailyMetric.revenue).desc())
                .limit(5)
            )
            top_skus = [
                TopSKUSummaryDTO(
                    internal_sku=row.sku,
                    revenue=Decimal(row.revenue),
                    profit=Decimal(row.net_profit),
                    units_sold=int(row.units_sold or 0),
                )
                for row in top_rows.all()
            ]

            sku_count = (
                await self.db.execute(
                    select(func.count(func.distinct(SkuDailyMetric.sku))).where(
                        SkuDailyMetric.user_id == self.user_id,
                        SkuDailyMetric.marketplace == marketplace,
                        SkuDailyMetric.metric_date >= period_start,
                        SkuDailyMetric.metric_date <= period_end,
                    )
                )
            ).scalar_one()

            cov = await CostCoverageService(self.db, self.user_id).analyze(
                marketplace=marketplace,
                period=CoveragePeriod(start=period_start, end=period_end),
                limit=1,
            )
            trust = classify_profit_trust(cov.sku_cost_coverage_pct)
            profit_out, margin, top_skus = apply_profit_trust_to_ai_metrics(
                trust=trust,
                total_profit=total_profit_d if total_profit_d != 0 else None,
                margin_pct=margin,
                top_skus=top_skus,
            )
            if trust != "full":
                anomalies.append(
                    AnomalyDTO(
                        type="data_quality",
                        severity="medium",
                        confidence=Decimal("0.95"),
                        message=(
                            "Себестоимость не покрывает продажи полностью; "
                            "прибыль и маржа в ответе ИИ не интерпретировать как факт."
                        ),
                    )
                )

            return AnalyticsProcessor.prepare_ai_insight(
                report_id=report.id,
                report_date=period_end,
                marketplace_type=marketplace.value,
                sku_count=int(sku_count or 0),
                total_revenue=total_revenue_d if total_revenue_d > 0 else None,
                total_profit=profit_out if profit_out is not None and profit_out != 0 else None,
                margin=margin,
                top_skus_summary=top_skus,
                anomalies=anomalies,
            )

    async def _insight_input_for_period(
        self,
        *,
        marketplace: Marketplace,
        period_start: date,
        period_end: date,
    ) -> AIInsightInputDTO | None:
        report: Report | None = None
        total_revenue_d = Decimal("0")
        total_profit_d = Decimal("0")
        margin: Decimal | None = None
        top_skus: list[TopSKUSummaryDTO] = []
        sku_count = 0

        async with TenantSession.transaction(self.db, self.user_id):
            report = await self._resolve_report_for_ai(None)
            if report is None:
                return None

            totals = await self.db.execute(
                select(
                    func.coalesce(func.sum(DailyAggregate.revenue), 0),
                    func.coalesce(func.sum(DailyAggregate.net_profit), 0),
                ).where(
                    DailyAggregate.user_id == self.user_id,
                    DailyAggregate.marketplace == marketplace,
                    DailyAggregate.aggregate_date >= period_start,
                    DailyAggregate.aggregate_date <= period_end,
                )
            )
            total_revenue, total_profit = totals.one()
            total_revenue_d = Decimal(total_revenue)
            total_profit_d = Decimal(total_profit)
            margin = (total_profit_d / total_revenue_d) * Decimal("100") if total_revenue_d > 0 else None

            top_rows = await self.db.execute(
                select(
                    SkuDailyMetric.sku,
                    func.sum(SkuDailyMetric.revenue).label("revenue"),
                    func.sum(SkuDailyMetric.net_profit).label("net_profit"),
                    func.sum(SkuDailyMetric.units_sold).label("units_sold"),
                )
                .where(
                    SkuDailyMetric.user_id == self.user_id,
                    SkuDailyMetric.marketplace == marketplace,
                    SkuDailyMetric.metric_date >= period_start,
                    SkuDailyMetric.metric_date <= period_end,
                )
                .group_by(SkuDailyMetric.sku)
                .order_by(func.sum(SkuDailyMetric.revenue).desc())
                .limit(5)
            )
            top_skus = [
                TopSKUSummaryDTO(
                    internal_sku=row.sku,
                    revenue=Decimal(row.revenue),
                    profit=Decimal(row.net_profit),
                    units_sold=int(row.units_sold or 0),
                )
                for row in top_rows.all()
            ]

            sku_count = (
                await self.db.execute(
                    select(func.count(func.distinct(SkuDailyMetric.sku))).where(
                        SkuDailyMetric.user_id == self.user_id,
                        SkuDailyMetric.marketplace == marketplace,
                        SkuDailyMetric.metric_date >= period_start,
                        SkuDailyMetric.metric_date <= period_end,
                    )
                )
            ).scalar_one()

        cov = await CostCoverageService(self.db, self.user_id).analyze(
            marketplace=marketplace,
            period=CoveragePeriod(start=period_start, end=period_end),
            limit=1,
        )
        trust = classify_profit_trust(cov.sku_cost_coverage_pct)
        profit_out, margin, top_skus = apply_profit_trust_to_ai_metrics(
            trust=trust,
            total_profit=total_profit_d,
            margin_pct=margin,
            top_skus=top_skus,
        )

        # Add deterministic trust / confidence signals as anomalies (visible to prompts via metrics_snapshot.anomalies).
        anomalies: list[AnomalyDTO] = []
        try:
            cov = await CostCoverageService(self.db, self.user_id).analyze(
                marketplace=marketplace,
                period=CoveragePeriod(start=period_start, end=period_end),
                limit=1,
            )
            if cov.cost_completeness_score is not None and cov.cost_completeness_score < Decimal("70"):
                anomalies.append(
                    AnomalyDTO(
                        type="data_quality",
                        severity="medium",
                        confidence=Decimal("0.9"),
                        message="Низкая уверенность в марже: себестоимость покрыта частично или устарела.",
                    )
                )
        except Exception:
            pass
        try:
            rec = await ReconciliationService(self.db, self.user_id).reconcile(
                marketplace=marketplace,
                period=ReconciliationPeriod(start=period_start, end=period_end),
            )
            if any(w.code == "payout_mismatch" for w in rec.warnings):
                anomalies.append(
                    AnomalyDTO(
                        type="data_quality",
                        severity="medium",
                        confidence=Decimal("0.8"),
                        message="Есть расхождение выплат: часть компонентов может отсутствовать или быть неполной.",
                    )
                )
        except Exception:
            pass

        return AnalyticsProcessor.prepare_ai_insight(
            report_id=report.id,
            report_date=period_end,
            marketplace_type=marketplace.value,
            sku_count=int(sku_count or 0),
            total_revenue=total_revenue_d if total_revenue_d > 0 else None,
            total_profit=profit_out if profit_out is not None and profit_out != 0 else None,
            margin=margin,
            top_skus_summary=top_skus,
            anomalies=anomalies,
        )

    async def _resolve_report_for_ai(self, report_id: UUID | None) -> Report | None:
        if report_id is not None:
            report = await self.db.get(Report, report_id)
            if report is None or report.user_id != self.user_id:
                return None
            return report
        result = await self.db.execute(
            select(Report)
            .where(Report.user_id == self.user_id)
            .where(Report.row_count.is_not(None))
            .where(Report.row_count > 0)
            .order_by(Report.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
