"""Single-request dashboard aggregation (parallel server-side fan-out).

Phase 9.18-B: slim first-screen payload — omit AI priority queues / full
recommendation bodies / queue job rows / cost-coverage SKU tables that the
dashboard UI does not render. Ops branches run only for platform admins.

Phase 9.18-D P1: one TenantSession per branch (A); one runtime/freshness (B+C);
one seller KPI + integrity validate per period (D) via DashboardQueryCache.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from typing import TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.core.security_context import TenantSession
from app.core.user_roles import is_platform_admin
from app.models.report import Marketplace
from app.models.user import User
from app.runtime.control_plane.state import (
    RuntimeHealthSeverity,
    TenantOperationalState,
    WorkloadState,
)
from app.schemas.ai_intelligence import (
    AIOperationalStatusResponse,
    PaginatedRecommendationsResponse,
    TodaysFocusResponse,
)
from app.schemas.ai import PageMeta as AiPageMeta
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
from app.schemas.ops import PageMeta as OpsPageMeta, PaginatedQueueResponse
from app.schemas.ops_runtime import (
    RuntimeHealthResponse,
    RuntimeQueueSnapshotResponse,
    RuntimeRebuildSnapshotResponse,
    RuntimeSummaryResponse,
)
from app.services.ai_service import AIService
from app.services.analytics_service import AnalyticsService, Period
from app.services.cost_coverage_service import CostCoverageService, CoveragePeriod
from app.services.dashboard_query_cache import DashboardQueryCache
from app.services.ops_service import OpsService

T = TypeVar("T")

# Dashboard only shows a short sample of missing SKUs in trust banners.
_MISSING_SKUS_CAP = 20


def _empty_runtime() -> RuntimeSummaryResponse:
    return RuntimeSummaryResponse(
        tenant_state=TenantOperationalState.HEALTHY,
        workload_state=WorkloadState.IDLE,
        queue=RuntimeQueueSnapshotResponse(
            pending_count=0,
            processing_count=0,
            dead_letter_count=0,
        ),
        rebuild=RuntimeRebuildSnapshotResponse(
            pending_dispatch=0,
            deferred=0,
            running=0,
            failed=0,
        ),
        health=RuntimeHealthResponse(
            overall_score=100.0,
            overall_severity=RuntimeHealthSeverity.OK,
            dimensions=[],
            recommendations=[],
        ),
        policy_autonomy_enabled=False,
        policy_queue_overload_threshold=0,
    )


def _empty_ai_ops() -> AIOperationalStatusResponse:
    return AIOperationalStatusResponse(
        overall_score=100.0,
        degraded_intelligence_mode=False,
        runs_total=0,
        success_rate=1.0,
        pending_approvals=0,
        avg_confidence=None,
        recommendations=[],
    )


def _slim_todays_focus(focus_raw) -> TodaysFocusResponse:
    """Keep fields the dashboard renders; drop priority_queue payload bloat."""
    return TodaysFocusResponse(
        generated_at=focus_raw.generated_at,
        headline=focus_raw.headline,
        requires_attention_today=[],
        can_wait=[],
        dangerous=list(focus_raw.dangerous)[:5],
        highest_upside=[],
        top_actions=[],
        critical_alerts=[],
        quick_wins=[],
        priority_queue=[],
        advisory_notice=focus_raw.advisory_notice,
    )


def _slim_cost_coverage(cost_coverage) -> CostCoverageResponse:
    payload = CostCoverageResponse.model_validate(cost_coverage)
    if len(payload.missing_skus) > _MISSING_SKUS_CAP:
        payload = payload.model_copy(
            update={"missing_skus": list(payload.missing_skus)[:_MISSING_SKUS_CAP]}
        )
    if payload.items:
        payload = payload.model_copy(update={"items": []})
    return payload


class DashboardService:
    def __init__(self, db: AsyncSession, user: User) -> None:
        self.db = db
        self.user = user

    async def _run(self, fn) -> T:
        """Each fan-out task: own DB session + one TenantSession (no repeated set_config)."""
        async with SessionLocal() as session:
            async with TenantSession.transaction(session, self.user.id):
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
        admin = is_platform_admin(user.role)
        cache = DashboardQueryCache()

        def analytics(db: AsyncSession) -> AnalyticsService:
            return AnalyticsService(db, user, query_cache=cache)

        # Critical path for first screen (all roles).
        coros: list = [
            self._run(lambda db: AIService(db, user_id).todays_focus()),
            self._run(
                lambda db: analytics(db).revenue_summary(marketplace=marketplace, period=period)
            ),
            self._run(
                lambda db: analytics(db).revenue_trend(marketplace=marketplace, period=period)
            ),
            self._run(
                lambda db: analytics(db).financial_summary(marketplace=marketplace, period=period)
            ),
            self._run(
                lambda db: analytics(db).financial_trends(marketplace=marketplace, period=period)
            ),
            self._run(
                lambda db: analytics(db).top_skus(
                    marketplace=marketplace, period=period, limit=5, sort="revenue"
                )
            ),
            self._run(lambda db: analytics(db).coverage(for_period=period)),
            self._run(
                lambda db: CostCoverageService(
                    db, user_id, query_cache=cache, user=user
                ).analyze(
                    marketplace=marketplace,
                    period=CoveragePeriod(start=start, end=end),
                    # Dashboard trust UI uses aggregates + missing_skus sample only.
                    limit=0,
                )
            ),
        ]
        # Admin KPI strip: status counts / AI mode / recommendation total.
        # runtime comes from shared cache (B) — no separate fan-out branch.
        if admin:
            coros.extend(
                [
                    self._run(lambda db: OpsService(db, user).list_queue_jobs(skip=0, limit=0)),
                    self._run(lambda db: AIService(db, user_id).operational_status()),
                    self._run(lambda db: AIService(db, user_id).count_recommendations()),
                ]
            )

        compare_idx: int | None = None
        if compare_start is not None and compare_end is not None:
            compare_period = Period(start=compare_start, end=compare_end)
            compare_idx = len(coros)
            coros.append(
                self._run(
                    lambda db: analytics(db).revenue_summary(
                        marketplace=marketplace, period=compare_period
                    )
                )
            )

        results = await asyncio.gather(*coros)

        focus_raw = results[0]
        revenue = results[1]
        revenue_trend = results[2]
        finance = results[3]
        finance_trend = results[4]
        top_skus = results[5]
        coverage = results[6]
        cost_coverage = results[7]

        if admin:
            _queue_rows, queue_total, status_counts = results[8]
            ai_ops_raw = results[9]
            rec_total = int(results[10])
            queue = PaginatedQueueResponse(
                items=[],
                page=OpsService.page_meta(queue_total, 0, 0),
                status_counts=status_counts,
            )
            # Shared runtime snapshot from analytics freshness path (B).
            if cache.runtime is not None:
                runtime_payload = cache.runtime
            else:
                # Extremely unlikely if analytics ran; fall back once.
                async with SessionLocal() as session:
                    async with TenantSession.transaction(session, user_id):
                        runtime_payload = await OpsService(session, user).runtime_summary()
            ai_ops = AIOperationalStatusResponse(
                overall_score=ai_ops_raw.overall_score,
                degraded_intelligence_mode=ai_ops_raw.degraded_intelligence_mode,
                runs_total=ai_ops_raw.runs_total,
                success_rate=ai_ops_raw.success_rate,
                pending_approvals=ai_ops_raw.pending_approvals,
                avg_confidence=ai_ops_raw.avg_confidence,
                recommendations=list(ai_ops_raw.recommendations),
            )
            recommendations = PaginatedRecommendationsResponse(
                items=[],
                page=AiPageMeta(total=rec_total, skip=0, limit=0),
            )
        else:
            queue = PaginatedQueueResponse(
                items=[],
                page=OpsPageMeta(total=0, skip=0, limit=0),
                status_counts={},
            )
            runtime_payload = cache.runtime if cache.runtime is not None else _empty_runtime()
            ai_ops = _empty_ai_ops()
            recommendations = PaginatedRecommendationsResponse(
                items=[],
                page=AiPageMeta(total=0, skip=0, limit=0),
            )

        revenue_compare = results[compare_idx] if compare_idx is not None else None

        return DashboardSummaryResponse(
            queue=queue,
            runtime=runtime_payload,
            ai_ops=ai_ops,
            todays_focus=_slim_todays_focus(focus_raw),
            recommendations=recommendations,
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
            cost_coverage=_slim_cost_coverage(cost_coverage),
            generated_at=datetime.now(UTC).isoformat(),
        )
