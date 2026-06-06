"""Aggregated dashboard payload (replaces N parallel client requests)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.ai_intelligence import AIOperationalStatusResponse, TodaysFocusResponse
from app.schemas.analytics import (
    AnalyticsCoverageResponse,
    CostCoverageResponse,
    FinancialKpiSummaryResponse,
    FinancialTrendsResponse,
    RevenueKpiSummaryResponse,
    RevenueTrendResponse,
    TopSkusResponse,
)
from app.schemas.ai_intelligence import PaginatedRecommendationsResponse
from app.schemas.ops import PaginatedQueueResponse
from app.schemas.ops_runtime import RuntimeSummaryResponse


class DashboardSummaryResponse(BaseModel):
    queue: PaginatedQueueResponse
    runtime: RuntimeSummaryResponse
    ai_ops: AIOperationalStatusResponse
    todays_focus: TodaysFocusResponse
    recommendations: PaginatedRecommendationsResponse
    revenue_summary: RevenueKpiSummaryResponse
    revenue_summary_compare: RevenueKpiSummaryResponse | None = None
    revenue_trend_daily: RevenueTrendResponse
    finance_summary: FinancialKpiSummaryResponse
    finance_trend_daily: FinancialTrendsResponse
    top_skus: TopSkusResponse
    coverage: AnalyticsCoverageResponse
    cost_coverage: CostCoverageResponse | None = None
    generated_at: str = Field(..., description="ISO-8601 UTC timestamp")
