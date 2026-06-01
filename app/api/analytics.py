"""Read-only seller KPI analytics endpoints (tenant-scoped)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.report import Marketplace
from app.models.user import User
from app.schemas.analytics import (
    AbcAnalysisResponse,
    AnalyticsCoverageResponse,
    CostCoverageResponse,
    FinancialKpiSummaryResponse,
    FinancialTrendsResponse,
    InventoryDeadStockResponse,
    InventoryEconomicsResponse,
    InventoryRiskIndicatorsResponse,
    InventorySlowMoversResponse,
    PeriodComparisonResponse,
    ReconciliationResponse,
    RevenueKpiSummaryResponse,
    RevenueTrendResponse,
    SkuDrilldownResponse,
    SkuEconomicsResponse,
    TopSkusResponse,
    WarehouseAnalyticsResponse,
)
from app.services.analytics_service import AnalyticsService, Period
from app.services.cost_coverage_service import CostCoverageService, CoveragePeriod
from app.services.reconciliation_service import ReconciliationPeriod, ReconciliationService

router = APIRouter()


def _marketplace(value: str) -> Marketplace:
    return Marketplace(value.lower())


def _period(start: date, end: date) -> Period:
    return Period(start=start, end=end)


@router.get("/kpis/summary", response_model=RevenueKpiSummaryResponse)
async def revenue_summary(
    marketplace: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RevenueKpiSummaryResponse:
    svc = AnalyticsService(db, current_user)
    return await svc.revenue_summary(marketplace=_marketplace(marketplace), period=_period(start, end))


@router.get("/kpis/trends/daily", response_model=RevenueTrendResponse)
async def revenue_trend_daily(
    marketplace: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RevenueTrendResponse:
    svc = AnalyticsService(db, current_user)
    return await svc.revenue_trend(marketplace=_marketplace(marketplace), period=_period(start, end))


@router.get("/kpis/top-skus", response_model=TopSkusResponse)
async def top_skus(
    marketplace: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    limit: int = Query(10, ge=1, le=100),
    sort: str = Query("revenue"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TopSkusResponse:
    svc = AnalyticsService(db, current_user)
    return await svc.top_skus(
        marketplace=_marketplace(marketplace),
        period=_period(start, end),
        limit=limit,
        sort=sort,
    )


@router.get("/kpis/warehouses", response_model=WarehouseAnalyticsResponse)
async def warehouse_analytics(
    snapshot_date: date = Query(...),
    semantics_version: str = Query("1.0"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WarehouseAnalyticsResponse:
    svc = AnalyticsService(db, current_user)
    return await svc.warehouse_analytics(
        snapshot_date=snapshot_date,
        semantics_version=semantics_version,
    )


@router.get("/kpis/period-compare", response_model=PeriodComparisonResponse)
async def period_compare(
    marketplace: str = Query(...),
    a_start: date = Query(...),
    a_end: date = Query(...),
    b_start: date = Query(...),
    b_end: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PeriodComparisonResponse:
    svc = AnalyticsService(db, current_user)
    return await svc.period_compare(
        marketplace=_marketplace(marketplace),
        a=_period(a_start, a_end),
        b=_period(b_start, b_end),
    )


@router.get("/kpis/abc", response_model=AbcAnalysisResponse)
async def abc_analysis(
    marketplace: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AbcAnalysisResponse:
    svc = AnalyticsService(db, current_user)
    return await svc.abc_analysis(marketplace=_marketplace(marketplace), period=_period(start, end))


@router.get("/kpis/inventory-risk", response_model=InventoryRiskIndicatorsResponse)
async def inventory_risk(
    snapshot_date: date = Query(...),
    semantics_version: str = Query("1.0"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InventoryRiskIndicatorsResponse:
    svc = AnalyticsService(db, current_user)
    return await svc.inventory_risk(snapshot_date=snapshot_date, semantics_version=semantics_version)


@router.get("/coverage", response_model=AnalyticsCoverageResponse)
async def analytics_coverage(
    semantics_version: str = Query("1.0"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalyticsCoverageResponse:
    svc = AnalyticsService(db, current_user)
    return await svc.coverage(semantics_version=semantics_version)


@router.get("/kpis/finance/summary", response_model=FinancialKpiSummaryResponse)
async def financial_kpis_summary(
    marketplace: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FinancialKpiSummaryResponse:
    svc = AnalyticsService(db, current_user)
    return await svc.financial_summary(marketplace=_marketplace(marketplace), period=_period(start, end))


@router.get("/kpis/finance/trends/daily", response_model=FinancialTrendsResponse)
async def financial_kpis_trends_daily(
    marketplace: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FinancialTrendsResponse:
    svc = AnalyticsService(db, current_user)
    return await svc.financial_trends(marketplace=_marketplace(marketplace), period=_period(start, end))


@router.get("/sku-economics", response_model=SkuEconomicsResponse)
async def sku_economics(
    marketplace: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort: str = Query("contribution_margin"),
    order: str = Query("desc"),
    q: str | None = Query(None, description="SKU contains"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SkuEconomicsResponse:
    svc = AnalyticsService(db, current_user)
    return await svc.sku_economics(
        marketplace=_marketplace(marketplace),
        period=_period(start, end),
        skip=skip,
        limit=limit,
        sort=sort,
        order=order,
        sku_query=q,
    )


@router.get("/sku-economics/sku/{sku}/drilldown", response_model=SkuDrilldownResponse)
async def sku_drilldown(
    sku: str,
    marketplace: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    semantics_version: str = Query("1.0"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SkuDrilldownResponse:
    svc = AnalyticsService(db, current_user)
    return await svc.sku_drilldown(
        marketplace=_marketplace(marketplace),
        sku=sku,
        period=_period(start, end),
        semantics_version=semantics_version,
    )


@router.get("/cost-coverage", response_model=CostCoverageResponse)
async def cost_coverage(
    marketplace: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    limit: int = Query(50, ge=1, le=200),
    q: str | None = Query(None, description="SKU contains"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CostCoverageResponse:
    svc = CostCoverageService(db, current_user.id)
    return await svc.analyze(
        marketplace=_marketplace(marketplace),
        period=CoveragePeriod(start=start, end=end),
        limit=limit,
        sku_query=q,
    )


@router.get("/reconciliation/period", response_model=ReconciliationResponse)
async def reconciliation_period(
    marketplace: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReconciliationResponse:
    svc = ReconciliationService(db, current_user.id)
    return await svc.reconcile(
        marketplace=_marketplace(marketplace),
        period=ReconciliationPeriod(start=start, end=end),
    )


@router.get("/inventory-economics", response_model=InventoryEconomicsResponse)
async def inventory_economics(
    marketplace: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    limit: int = Query(50, ge=1, le=200),
    q: str | None = Query(None, description="SKU contains"),
    semantics_version: str = Query("1.0"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InventoryEconomicsResponse:
    svc = AnalyticsService(db, current_user)
    return await svc.inventory_economics(
        marketplace=_marketplace(marketplace),
        period=_period(start, end),
        limit=limit,
        sku_query=q,
        semantics_version=semantics_version,
    )


@router.get("/inventory-economics/slow-movers", response_model=InventorySlowMoversResponse)
async def inventory_slow_movers(
    marketplace: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    threshold_days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
    semantics_version: str = Query("1.0"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InventorySlowMoversResponse:
    svc = AnalyticsService(db, current_user)
    return await svc.inventory_slow_movers(
        marketplace=_marketplace(marketplace),
        period=_period(start, end),
        threshold_days=threshold_days,
        limit=limit,
        semantics_version=semantics_version,
    )


@router.get("/inventory-economics/dead-stock", response_model=InventoryDeadStockResponse)
async def inventory_dead_stock(
    marketplace: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    threshold_days: int = Query(60, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
    semantics_version: str = Query("1.0"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InventoryDeadStockResponse:
    svc = AnalyticsService(db, current_user)
    return await svc.inventory_dead_stock(
        marketplace=_marketplace(marketplace),
        period=_period(start, end),
        threshold_days=threshold_days,
        limit=limit,
        semantics_version=semantics_version,
    )
