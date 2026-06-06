"""Analytics read-layer schemas (read-only projections)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.report import Marketplace


class AnalyticsFreshnessMeta(BaseModel):
    model_config = ConfigDict(strict=True)

    semantics_version: str = Field(min_length=1, max_length=16, default="1.0")
    data_as_of: date | None = None
    rebuild_running: int = 0
    rebuild_pending: int = 0
    queue_processing: int = 0
    queue_pending: int = 0
    dead_letters: int = 0
    stale_data_warning: bool = False
    degraded_mode: bool = False
    generated_at: datetime


class IntegrityWarning(BaseModel):
    """
    Deterministic financial integrity warning for seller-facing trust UX.

    This is not an "AI insight" and must be derived only from governed projections
    / ledgers under tenant RLS.
    """

    model_config = ConfigDict(strict=True)

    code: str = Field(min_length=1, max_length=64)
    severity: str = Field(min_length=1, max_length=16)  # info|warning|critical
    message: str = Field(min_length=1, max_length=512)
    context: dict[str, str] | None = None


class AnalyticsIntegrityMeta(BaseModel):
    model_config = ConfigDict(strict=True)

    warnings: list[IntegrityWarning] = Field(default_factory=list)
    financial_completeness_score: Decimal | None = None  # 0..100 (best-effort heuristic)
    sku_cost_coverage_pct: Decimal | None = None
    profit_metrics_trust: str | None = None  # full | partial | insufficient


class RevenueKpiSummary(BaseModel):
    model_config = ConfigDict(strict=True)

    total_revenue: Decimal = Field(default=Decimal("0"))
    total_profit: Decimal | None = None
    margin_pct: Decimal | None = None
    units_sold: int = 0
    average_check: Decimal | None = None


class RevenueKpiSummaryResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    marketplace: Marketplace
    period_start: date
    period_end: date
    kpis: RevenueKpiSummary
    freshness: AnalyticsFreshnessMeta
    integrity: AnalyticsIntegrityMeta | None = None


class TrendPoint(BaseModel):
    model_config = ConfigDict(strict=True)

    date: date
    revenue: Decimal
    net_profit: Decimal
    margin_pct: Decimal | None = None
    units_sold: int


class RevenueTrendResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    marketplace: Marketplace
    period_start: date
    period_end: date
    points: list[TrendPoint]
    freshness: AnalyticsFreshnessMeta
    integrity: AnalyticsIntegrityMeta | None = None


class TopSkuRow(BaseModel):
    model_config = ConfigDict(strict=True)

    sku: str = Field(min_length=1, max_length=128)
    revenue: Decimal
    net_profit: Decimal
    margin_pct: Decimal | None = None
    units_sold: int
    contribution_pct: Decimal | None = None


class TopSkusResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    marketplace: Marketplace
    period_start: date
    period_end: date
    sort: str
    items: list[TopSkuRow]
    freshness: AnalyticsFreshnessMeta
    integrity: AnalyticsIntegrityMeta | None = None


class WarehouseRow(BaseModel):
    model_config = ConfigDict(strict=True)

    warehouse_name: str | None = None
    opening_stock: int
    inbound_units: int
    sold_units: int
    returned_units: int
    lost_units: int
    writeoff_units: int
    expected_closing_stock: int
    actual_stock: int
    discrepancy_units: int
    discrepancy_cost: Decimal
    discrepancy_sale_value: Decimal


class WarehouseAnalyticsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    snapshot_date: date
    semantics_version: str
    items: list[WarehouseRow]
    freshness: AnalyticsFreshnessMeta
    integrity: AnalyticsIntegrityMeta | None = None


class PeriodComparisonResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    marketplace: Marketplace
    a_start: date
    a_end: date
    b_start: date
    b_end: date
    a: RevenueKpiSummary
    b: RevenueKpiSummary
    delta_revenue: Decimal
    delta_profit: Decimal
    delta_margin_pct: Decimal | None = None
    freshness: AnalyticsFreshnessMeta
    integrity: AnalyticsIntegrityMeta | None = None


class AbcBucketRow(BaseModel):
    model_config = ConfigDict(strict=True)

    bucket: str  # A/B/C
    sku_count: int
    revenue: Decimal
    revenue_pct: Decimal


class AbcAnalysisResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    marketplace: Marketplace
    period_start: date
    period_end: date
    buckets: list[AbcBucketRow]
    freshness: AnalyticsFreshnessMeta
    integrity: AnalyticsIntegrityMeta | None = None


class InventoryRiskIndicatorsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    snapshot_date: date
    high_discrepancy_warehouses: int
    discrepancy_cost_total: Decimal
    stale_data_warning: bool
    freshness: AnalyticsFreshnessMeta
    integrity: AnalyticsIntegrityMeta | None = None


class MissingPeriodRange(BaseModel):
    model_config = ConfigDict(strict=True)

    start: date
    end: date
    missing_days: int


class UploadedReportTypeRow(BaseModel):
    model_config = ConfigDict(strict=True)

    marketplace: Marketplace
    report_type: str
    count: int


class ReportRecommendation(BaseModel):
    model_config = ConfigDict(strict=True)

    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=512)
    severity: str = Field(min_length=1, max_length=16)  # info|warning|critical


class AnalyticsCoverageResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    marketplaces: list[Marketplace] = Field(default_factory=list)
    available_min_date: date | None = None
    available_max_date: date | None = None
    available_by_marketplace: dict[str, dict[str, date | None]] = Field(default_factory=dict)
    uploaded_report_types: list[UploadedReportTypeRow] = Field(default_factory=list)
    missing_periods: list[MissingPeriodRange] = Field(default_factory=list)
    recommendations: list[ReportRecommendation] = Field(default_factory=list)
    financial_completeness_score: Decimal | None = None
    freshness: AnalyticsFreshnessMeta
    warnings: list[IntegrityWarning] = Field(default_factory=list)


class FinancialKpiSummary(BaseModel):
    model_config = ConfigDict(strict=True)

    sales_revenue: Decimal = Decimal("0")
    returns_amount: Decimal = Decimal("0")
    payout: Decimal = Decimal("0")
    commission: Decimal = Decimal("0")
    logistics: Decimal = Decimal("0")
    storage_fee: Decimal = Decimal("0")
    acquiring: Decimal = Decimal("0")
    advertisement: Decimal = Decimal("0")
    penalties: Decimal = Decimal("0")
    deductions: Decimal = Decimal("0")
    compensation: Decimal = Decimal("0")

    gross_profit: Decimal | None = None
    margin_pct: Decimal | None = None
    return_rate_pct: Decimal | None = None
    total_to_pay: Decimal = Decimal("0")


class FinancialKpiSummaryResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    marketplace: Marketplace
    period_start: date
    period_end: date
    kpis: FinancialKpiSummary
    freshness: AnalyticsFreshnessMeta
    integrity: AnalyticsIntegrityMeta | None = None


class FinancialTrendPoint(BaseModel):
    model_config = ConfigDict(strict=True)

    date: date
    sales_revenue: Decimal = Decimal("0")
    gross_profit: Decimal = Decimal("0")
    margin_pct: Decimal | None = None
    logistics: Decimal = Decimal("0")
    advertisement: Decimal = Decimal("0")
    payout: Decimal = Decimal("0")
    returns_amount: Decimal = Decimal("0")


class FinancialTrendsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    marketplace: Marketplace
    period_start: date
    period_end: date
    points: list[FinancialTrendPoint]
    freshness: AnalyticsFreshnessMeta
    integrity: AnalyticsIntegrityMeta | None = None


class SkuEconomicsRow(BaseModel):
    model_config = ConfigDict(strict=True)

    sku: str
    revenue: Decimal
    contribution_margin: Decimal
    gross_profit: Decimal
    cogs: Decimal
    returns_amount: Decimal
    payout: Decimal
    commissions: Decimal
    logistics: Decimal
    storage: Decimal
    ads: Decimal
    penalties: Decimal
    margin_pct: Decimal | None = None
    return_rate: Decimal | None = None
    ad_cost_ratio: Decimal | None = None
    logistics_burden: Decimal | None = None


class SkuEconomicsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    marketplace: Marketplace
    period_start: date
    period_end: date
    total: int
    items: list[SkuEconomicsRow]
    freshness: AnalyticsFreshnessMeta
    integrity: AnalyticsIntegrityMeta | None = None


class CostCoverageSkuRow(BaseModel):
    model_config = ConfigDict(strict=True)

    sku: str
    units_sold: int
    revenue: Decimal
    cogs: Decimal
    cost_coverage_pct: Decimal | None = None
    last_cost_effective_from: date | None = None
    warnings: list[IntegrityWarning] = Field(default_factory=list)


class CostCoverageResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    marketplace: Marketplace
    period_start: date
    period_end: date
    total_skus: int
    covered_skus: int
    sku_cost_coverage_pct: Decimal | None = None
    cost_completeness_score: Decimal | None = None
    items: list[CostCoverageSkuRow] = Field(default_factory=list)
    freshness: AnalyticsFreshnessMeta
    warnings: list[IntegrityWarning] = Field(default_factory=list)


class ReconciliationBreakdown(BaseModel):
    model_config = ConfigDict(strict=True)

    revenue: Decimal
    returns_amount: Decimal
    commissions: Decimal
    logistics: Decimal
    storage: Decimal
    ads: Decimal
    penalties: Decimal
    acquiring: Decimal
    deductions: Decimal
    compensation: Decimal
    cogs: Decimal

    expected_payout: Decimal
    actual_payout: Decimal
    payout_difference: Decimal

    profit: Decimal
    payout_is_not_profit_explanation: str


class ReconciliationResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    marketplace: Marketplace
    period_start: date
    period_end: date
    breakdown: ReconciliationBreakdown
    freshness: AnalyticsFreshnessMeta
    warnings: list[IntegrityWarning] = Field(default_factory=list)


class InventoryEconomicsRow(BaseModel):
    model_config = ConfigDict(strict=True)

    sku: str
    stock_units: int
    sold_units: int
    avg_stock_units: Decimal | None = None
    turnover_ratio: Decimal | None = None  # sold_units / avg_stock_units
    turnover_days: Decimal | None = None  # (avg_stock_units / avg_daily_sold_units)
    frozen_capital: Decimal | None = None  # stock_units * unit_cost (best-effort)
    unit_cost: Decimal | None = None
    days_since_last_sale: int | None = None
    stock_risk: str | None = None  # ok|stockout|overstock


class InventoryEconomicsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    marketplace: Marketplace
    period_start: date
    period_end: date
    snapshot_date: date | None = None
    total_skus: int
    items: list[InventoryEconomicsRow]
    freshness: AnalyticsFreshnessMeta
    integrity: AnalyticsIntegrityMeta | None = None


class InventorySlowMoverRow(BaseModel):
    model_config = ConfigDict(strict=True)

    sku: str
    stock_units: int
    frozen_capital: Decimal | None = None
    unit_cost: Decimal | None = None
    days_since_last_sale: int


class InventorySlowMoversResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    marketplace: Marketplace
    period_start: date
    period_end: date
    snapshot_date: date | None = None
    threshold_days: int
    items: list[InventorySlowMoverRow]
    freshness: AnalyticsFreshnessMeta
    integrity: AnalyticsIntegrityMeta | None = None


class InventoryDeadStockRow(BaseModel):
    model_config = ConfigDict(strict=True)

    sku: str
    stock_units: int
    frozen_capital: Decimal | None = None
    unit_cost: Decimal | None = None
    days_since_last_sale: int


class InventoryDeadStockResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    marketplace: Marketplace
    period_start: date
    period_end: date
    snapshot_date: date | None = None
    threshold_days: int
    items: list[InventoryDeadStockRow]
    freshness: AnalyticsFreshnessMeta
    integrity: AnalyticsIntegrityMeta | None = None


class SkuEconomicsTrendPoint(BaseModel):
    model_config = ConfigDict(strict=True)

    date: date
    revenue: Decimal = Decimal("0")
    gross_profit: Decimal = Decimal("0")
    contribution_margin: Decimal = Decimal("0")
    margin_pct: Decimal | None = None
    returns_amount: Decimal = Decimal("0")
    logistics: Decimal = Decimal("0")
    ads: Decimal = Decimal("0")
    penalties: Decimal = Decimal("0")
    payout: Decimal = Decimal("0")
    stock_units: int | None = None  # best-effort from snapshots


class SkuDrilldownResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    marketplace: Marketplace
    sku: str
    period_start: date
    period_end: date
    points: list[SkuEconomicsTrendPoint]
    freshness: AnalyticsFreshnessMeta
    integrity: AnalyticsIntegrityMeta | None = None

