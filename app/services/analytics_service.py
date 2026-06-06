"""Read-only analytics query services (tenant-scoped via RLS)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.analytics.profit_trust import (
    apply_profit_trust_to_kpis,
    gate_margin_decimal,
    gate_profit_decimal,
)
from app.domain.economics.inventory_math import compute_turnover, days_since, stock_risk_label
from app.models.cost_history import CostHistory
from app.models.economics.sku_unit_economics import SkuUnitEconomicsDaily
from app.models.finance.aggregates import DailyAggregate, SkuDailyMetric
from app.models.finance.enums import LedgerOperationType
from app.models.finance.ledger import FinancialLedgerEntry
from app.models.inventory.snapshot import WarehouseStockSnapshot
from app.models.report import Marketplace, Report
from app.models.user import User
from app.schemas.analytics import (
    AbcAnalysisResponse,
    AbcBucketRow,
    AnalyticsCoverageResponse,
    AnalyticsFreshnessMeta,
    AnalyticsIntegrityMeta,
    FinancialKpiSummary,
    FinancialKpiSummaryResponse,
    FinancialTrendPoint,
    FinancialTrendsResponse,
    InventoryDeadStockResponse,
    InventoryDeadStockRow,
    InventoryEconomicsResponse,
    InventoryEconomicsRow,
    InventoryRiskIndicatorsResponse,
    InventorySlowMoverRow,
    InventorySlowMoversResponse,
    MissingPeriodRange,
    PeriodComparisonResponse,
    ReportRecommendation,
    RevenueKpiSummary,
    RevenueKpiSummaryResponse,
    RevenueTrendResponse,
    SkuDrilldownResponse,
    SkuEconomicsResponse,
    SkuEconomicsRow,
    SkuEconomicsTrendPoint,
    TopSkuRow,
    TopSkusResponse,
    TrendPoint,
    UploadedReportTypeRow,
    WarehouseAnalyticsResponse,
    WarehouseRow,
)
from app.services.base import TenantScopedService
from app.services.financial_integrity_service import FinancialIntegrityService, IntegrityPeriod
from app.services.ops_service import OpsService


@dataclass(frozen=True)
class Period:
    start: date
    end: date


class AnalyticsService(TenantScopedService):
    def __init__(self, db: AsyncSession, user: User) -> None:
        super().__init__(db, user_id=user.id)
        self.user = user

    async def _freshness(self, semantics_version: str = "1.0") -> AnalyticsFreshnessMeta:
        # Reuse existing operational snapshot to provide rebuild/queue context.
        runtime = await OpsService(self.db, self.user).runtime_summary()
        data_as_of = await self._max_aggregate_date()

        rebuild = runtime.rebuild
        queue = runtime.queue
        stale = (rebuild.running > 0) or (rebuild.pending_dispatch > 0)

        return AnalyticsFreshnessMeta(
            semantics_version=semantics_version,
            data_as_of=data_as_of,
            rebuild_running=rebuild.running,
            rebuild_pending=rebuild.pending_dispatch,
            queue_processing=queue.processing_count,
            queue_pending=queue.pending_count,
            dead_letters=queue.dead_letter_count,
            stale_data_warning=stale,
            degraded_mode=runtime.health.overall_severity.value.lower() in ("warning", "critical")
            if hasattr(runtime.health.overall_severity, "value")
            else False,
            generated_at=datetime.now(UTC),
        )

    async def _integrity(
        self,
        *,
        marketplace: Marketplace,
        period: Period | None = None,
        semantics_version: str = "1.0",
    ) -> AnalyticsIntegrityMeta | None:
        if period is None:
            return None
        svc = FinancialIntegrityService(self.db, self.user.id)
        return await svc.validate_period(
            marketplace=marketplace,
            period=IntegrityPeriod(start=period.start, end=period.end),
            semantics_version=semantics_version,
        )

    async def _max_aggregate_date(self) -> date | None:
        stmt = select(func.max(DailyAggregate.aggregate_date))
        res = await self.execute_with_rls(stmt)
        return cast(date | None, res.scalar_one_or_none())

    async def _latest_snapshot_date(self, *, period_end: date, semantics_version: str = "1.0") -> date | None:
        stmt = (
            select(func.max(WarehouseStockSnapshot.snapshot_date))
            .where(WarehouseStockSnapshot.snapshot_date <= period_end)
            .where(WarehouseStockSnapshot.semantics_version == semantics_version)
        )
        res = await self.execute_with_rls(stmt)
        return cast(date | None, res.scalar_one_or_none())

    async def _unit_costs_as_of(self, *, as_of: date) -> dict[str, Decimal]:
        """
        Best-effort effective-dated unit cost lookup per SKU.
        Deterministic: if multiple records exist, choose the one with latest effective_from.
        """
        max_eff = (
            select(
                CostHistory.internal_sku.label("sku"),
                func.max(CostHistory.effective_from).label("eff"),
            )
            .where(CostHistory.effective_from <= as_of)
            .where((CostHistory.effective_to.is_(None)) | (CostHistory.effective_to >= as_of))
            .group_by(CostHistory.internal_sku)
            .subquery()
        )
        stmt = (
            select(CostHistory.internal_sku, CostHistory.cost)
            .join(max_eff, (CostHistory.internal_sku == max_eff.c.sku) & (CostHistory.effective_from == max_eff.c.eff))
        )
        res = await self.execute_with_rls(stmt)
        return {str(sku): Decimal(cost) for sku, cost in res.all()}

    async def coverage(self, *, semantics_version: str = "1.0") -> AnalyticsCoverageResponse:
        freshness = await self._freshness(semantics_version)

        # Marketplaces detected from governed projections.
        mp_stmt = select(DailyAggregate.marketplace).distinct()
        mp_res = await self.execute_with_rls(mp_stmt)
        marketplaces = [row[0] for row in mp_res.all()]

        minmax_stmt = select(func.min(DailyAggregate.aggregate_date), func.max(DailyAggregate.aggregate_date))
        minmax_res = await self.execute_with_rls(minmax_stmt)
        min_date, max_date = minmax_res.one()

        # Per-marketplace ranges.
        by_marketplace: dict[str, dict[str, date | None]] = {}
        for mp in marketplaces:
            r_stmt = (
                select(func.min(DailyAggregate.aggregate_date), func.max(DailyAggregate.aggregate_date))
                .where(DailyAggregate.marketplace == mp)
            )
            r_res = await self.execute_with_rls(r_stmt)
            mp_min, mp_max = r_res.one()
            by_marketplace[mp.value] = {"min_date": mp_min, "max_date": mp_max}

        # Uploaded report types (best-effort; reports.status is legacy, but this still describes what was ingested).
        report_stmt = (
            select(Report.marketplace, Report.report_type, func.count(Report.id))
            .group_by(Report.marketplace, Report.report_type)
            .order_by(Report.marketplace.asc(), Report.report_type.asc())
        )
        report_res = await self.execute_with_rls(report_stmt)
        uploaded_types = [
            UploadedReportTypeRow(marketplace=mp, report_type=rt.value if hasattr(rt, "value") else str(rt), count=int(cnt))
            for mp, rt, cnt in report_res.all()
        ]

        # Missing periods / gaps: compute missing date ranges per marketplace from available aggregate days.
        missing_ranges: list[MissingPeriodRange] = []
        for mp in marketplaces:
            days_stmt = (
                select(DailyAggregate.aggregate_date)
                .where(DailyAggregate.marketplace == mp)
                .order_by(DailyAggregate.aggregate_date.asc())
            )
            days_res = await self.execute_with_rls(days_stmt)
            days = [d[0] for d in days_res.all()]
            if not days:
                continue
            missing_ranges.extend(_compute_missing_ranges(days, limit_ranges=50))

        recommendations: list[ReportRecommendation] = []
        warnings: list = []

        # Costs recommendation.
        integrity = await FinancialIntegrityService(self.db, self.user.id).validate_period(
            marketplace=marketplaces[0] if marketplaces else Marketplace.WILDBERRIES,
            period=IntegrityPeriod(start=min_date or date.today(), end=max_date or date.today()),
            semantics_version=semantics_version,
        ) if (min_date and max_date and marketplaces) else None
        if integrity:
            warnings.extend(integrity.warnings)
            if any(w.code == "missing_cost_basis" for w in integrity.warnings):
                recommendations.append(
                    ReportRecommendation(
                        code="upload_costs",
                        title="Upload costs to enable governed profit",
                        message="Costs are missing. Upload a costs file to compute gross profit and margin correctly (COGS is required).",
                        severity="warning",
                    )
                )

        # Ads recommendation (if there is revenue but no advertisement entries).
        if marketplaces and max_date:
            ads_stmt = select(func.count(FinancialLedgerEntry.id)).where(
                FinancialLedgerEntry.operation_type == LedgerOperationType.ADVERTISEMENT
            )
            ads_res = await self.execute_with_rls(ads_stmt)
            ads_count = int(ads_res.scalar_one() or 0)
            if ads_count == 0:
                recommendations.append(
                    ReportRecommendation(
                        code="upload_ads_report",
                        title="Upload ads report for ROI analytics",
                        message="No advertising spend detected in the ledger. Upload ads/promotions reports to enable ROI analysis.",
                        severity="info",
                    )
                )

        # Gap recommendation.
        if missing_ranges:
            recommendations.append(
                ReportRecommendation(
                    code="fill_missing_periods",
                    title="Fill missing periods for trustworthy trends",
                    message="There are gaps in available daily aggregates. Upload the missing report periods to improve trend and comparison accuracy.",
                    severity="warning",
                )
            )

        completeness_score = integrity.financial_completeness_score if integrity else None
        return AnalyticsCoverageResponse(
            marketplaces=marketplaces,
            available_min_date=min_date,
            available_max_date=max_date,
            available_by_marketplace=by_marketplace,
            uploaded_report_types=uploaded_types,
            missing_periods=missing_ranges,
            recommendations=recommendations,
            financial_completeness_score=completeness_score,
            freshness=freshness,
            warnings=warnings,
        )

    async def revenue_summary(
        self, *, marketplace: Marketplace, period: Period
    ) -> RevenueKpiSummaryResponse:
        stmt = (
            select(
                func.coalesce(func.sum(DailyAggregate.revenue), 0),
                func.coalesce(func.sum(DailyAggregate.net_profit), 0),
                func.coalesce(func.sum(DailyAggregate.units_sold), 0),
                func.avg(DailyAggregate.average_check),
            )
            .where(DailyAggregate.marketplace == marketplace)
            .where(DailyAggregate.aggregate_date >= period.start)
            .where(DailyAggregate.aggregate_date <= period.end)
        )
        res = await self.execute_with_rls(stmt)
        total_revenue, total_profit, units_sold, avg_check = res.one()
        margin = None
        if total_revenue and Decimal(total_revenue) > 0:
            margin = (Decimal(total_profit) / Decimal(total_revenue)) * Decimal("100")
        freshness = await self._freshness()
        integrity = await self._integrity(marketplace=marketplace, period=period, semantics_version=freshness.semantics_version)
        trust = integrity.profit_metrics_trust if integrity else "insufficient"
        profit_value, margin_value = apply_profit_trust_to_kpis(
            trust=trust or "insufficient",
            total_profit=Decimal(total_profit),
            margin_pct=margin,
        )
        if units_sold and int(units_sold) > 0:
            avg_check = Decimal(total_revenue) / Decimal(units_sold)
        else:
            avg_check = None
        return RevenueKpiSummaryResponse(
            marketplace=marketplace,
            period_start=period.start,
            period_end=period.end,
            kpis=RevenueKpiSummary(
                total_revenue=Decimal(total_revenue),
                total_profit=profit_value,
                margin_pct=margin_value,
                units_sold=int(units_sold or 0),
                average_check=avg_check,
            ),
            freshness=freshness,
            integrity=integrity,
        )

    async def financial_summary(self, *, marketplace: Marketplace, period: Period) -> FinancialKpiSummaryResponse:
        freshness = await self._freshness()

        # Ledger totals for the period by operation type.
        stmt = (
            select(FinancialLedgerEntry.operation_type, func.coalesce(func.sum(FinancialLedgerEntry.amount), 0))
            .where(FinancialLedgerEntry.operation_date >= period.start)
            .where(FinancialLedgerEntry.operation_date <= period.end)
            .group_by(FinancialLedgerEntry.operation_type)
        )
        res = await self.execute_with_rls(stmt)
        by_type = {op: Decimal(total) for op, total in res.all()}

        sales = by_type.get(LedgerOperationType.SALE, Decimal("0"))
        returns = abs(by_type.get(LedgerOperationType.RETURN, Decimal("0")))
        payout = by_type.get(LedgerOperationType.PAYOUT, Decimal("0"))
        commission = abs(by_type.get(LedgerOperationType.COMMISSION, Decimal("0")))
        logistics = abs(by_type.get(LedgerOperationType.LOGISTICS, Decimal("0")))
        storage_fee = abs(by_type.get(LedgerOperationType.STORAGE_FEE, Decimal("0")))
        acquiring = abs(by_type.get(LedgerOperationType.ACQUIRING, Decimal("0")))
        advertisement = abs(by_type.get(LedgerOperationType.ADVERTISEMENT, Decimal("0")))
        penalties = abs(by_type.get(LedgerOperationType.PENALTY, Decimal("0")))
        deductions = abs(by_type.get(LedgerOperationType.DEDUCTION, Decimal("0")))
        compensation = by_type.get(LedgerOperationType.COMPENSATION, Decimal("0"))

        agg_stmt = (
            select(
                func.coalesce(func.sum(DailyAggregate.revenue), 0),
                func.coalesce(func.sum(DailyAggregate.net_profit), 0),
            )
            .where(DailyAggregate.marketplace == marketplace)
            .where(DailyAggregate.aggregate_date >= period.start)
            .where(DailyAggregate.aggregate_date <= period.end)
        )
        agg_res = await self.execute_with_rls(agg_stmt)
        revenue_sum, profit_sum = agg_res.one()
        revenue = Decimal(revenue_sum)
        profit = Decimal(profit_sum)
        margin = (profit / revenue * Decimal("100")) if revenue > 0 else None
        return_rate = (returns / revenue * Decimal("100")) if revenue > 0 else None

        integrity = await self._integrity(marketplace=marketplace, period=period, semantics_version=freshness.semantics_version)
        trust = integrity.profit_metrics_trust if integrity else "insufficient"
        profit_value, margin_value = apply_profit_trust_to_kpis(
            trust=trust or "insufficient",
            total_profit=profit,
            margin_pct=margin,
        )
        return FinancialKpiSummaryResponse(
            marketplace=marketplace,
            period_start=period.start,
            period_end=period.end,
            kpis=FinancialKpiSummary(
                sales_revenue=sales,
                returns_amount=returns,
                payout=payout,
                commission=commission,
                logistics=logistics,
                storage_fee=storage_fee,
                acquiring=acquiring,
                advertisement=advertisement,
                penalties=penalties,
                deductions=deductions,
                compensation=compensation,
                gross_profit=profit_value,
                margin_pct=margin_value,
                return_rate_pct=return_rate,
                total_to_pay=payout,
            ),
            freshness=freshness,
            integrity=integrity,
        )

    async def financial_trends(self, *, marketplace: Marketplace, period: Period) -> FinancialTrendsResponse:
        freshness = await self._freshness()
        # Daily aggregates baseline for profit/margin.
        agg_stmt = (
            select(DailyAggregate)
            .where(DailyAggregate.marketplace == marketplace)
            .where(DailyAggregate.aggregate_date >= period.start)
            .where(DailyAggregate.aggregate_date <= period.end)
            .order_by(DailyAggregate.aggregate_date.asc())
        )
        agg_res = await self.execute_with_rls(agg_stmt)
        agg_rows = list(agg_res.scalars().all())

        # Ledger daily sums for selected ops.
        led_stmt = (
            select(
                FinancialLedgerEntry.operation_date,
                FinancialLedgerEntry.operation_type,
                func.coalesce(func.sum(FinancialLedgerEntry.amount), 0).label("total"),
            )
            .where(FinancialLedgerEntry.operation_date >= period.start)
            .where(FinancialLedgerEntry.operation_date <= period.end)
            .where(
                FinancialLedgerEntry.operation_type.in_(
                    (
                        LedgerOperationType.SALE,
                        LedgerOperationType.RETURN,
                        LedgerOperationType.PAYOUT,
                        LedgerOperationType.LOGISTICS,
                        LedgerOperationType.ADVERTISEMENT,
                    )
                )
            )
            .group_by(FinancialLedgerEntry.operation_date, FinancialLedgerEntry.operation_type)
            .order_by(FinancialLedgerEntry.operation_date.asc())
        )
        led_res = await self.execute_with_rls(led_stmt)
        by_day: dict[date, dict[LedgerOperationType, Decimal]] = {}
        for d, op, total in led_res.all():
            by_day.setdefault(d, {})[op] = Decimal(total)

        points: list[FinancialTrendPoint] = []
        integrity = await self._integrity(marketplace=marketplace, period=period, semantics_version=freshness.semantics_version)
        trust = integrity.profit_metrics_trust if integrity else "insufficient"
        for row in agg_rows:
            day = row.aggregate_date
            led = by_day.get(day, {})
            sales = led.get(LedgerOperationType.SALE, Decimal("0"))
            returns = abs(led.get(LedgerOperationType.RETURN, Decimal("0")))
            payout = led.get(LedgerOperationType.PAYOUT, Decimal("0"))
            logistics = abs(led.get(LedgerOperationType.LOGISTICS, Decimal("0")))
            ads = abs(led.get(LedgerOperationType.ADVERTISEMENT, Decimal("0")))
            profit_out, margin_out = apply_profit_trust_to_kpis(
                trust=trust or "insufficient",
                total_profit=row.net_profit,
                margin_pct=row.margin,
            )
            points.append(
                FinancialTrendPoint(
                    date=day,
                    sales_revenue=sales,
                    gross_profit=profit_out,
                    margin_pct=margin_out,
                    logistics=logistics,
                    advertisement=ads,
                    payout=payout,
                    returns_amount=returns,
                )
            )

        return FinancialTrendsResponse(
            marketplace=marketplace,
            period_start=period.start,
            period_end=period.end,
            points=points,
            freshness=freshness,
            integrity=integrity,
        )

    async def sku_economics(
        self,
        *,
        marketplace: Marketplace,
        period: Period,
        skip: int = 0,
        limit: int = 50,
        sort: str = "contribution_margin",
        order: str = "desc",
        sku_query: str | None = None,
    ) -> SkuEconomicsResponse:
        freshness = await self._freshness()
        sort_key = sort.lower()
        order_key = order.lower()

        sort_col = {
            "revenue": func.sum(SkuUnitEconomicsDaily.revenue),
            "gross_profit": func.sum(SkuUnitEconomicsDaily.gross_profit),
            "contribution_margin": func.sum(SkuUnitEconomicsDaily.contribution_margin),
            "returns": func.sum(SkuUnitEconomicsDaily.returns_amount),
            "ads": func.sum(SkuUnitEconomicsDaily.ads),
            "margin_pct": func.avg(SkuUnitEconomicsDaily.margin_pct),
            "return_rate": func.avg(SkuUnitEconomicsDaily.return_rate),
        }.get(sort_key, func.sum(SkuUnitEconomicsDaily.contribution_margin))

        base_filters = [
            SkuUnitEconomicsDaily.marketplace == marketplace,
            SkuUnitEconomicsDaily.metric_date >= period.start,
            SkuUnitEconomicsDaily.metric_date <= period.end,
        ]
        if sku_query:
            base_filters.append(SkuUnitEconomicsDaily.sku.ilike(f"%{sku_query}%"))

        total_stmt = select(func.count(func.distinct(SkuUnitEconomicsDaily.sku))).where(*base_filters)
        total_res = await self.execute_with_rls(total_stmt)
        total = int(total_res.scalar_one() or 0)

        stmt = (
            select(
                SkuUnitEconomicsDaily.sku,
                func.coalesce(func.sum(SkuUnitEconomicsDaily.revenue), 0).label("revenue"),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.contribution_margin), 0).label("contribution_margin"),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.gross_profit), 0).label("gross_profit"),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.cogs), 0).label("cogs"),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.returns_amount), 0).label("returns_amount"),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.payout), 0).label("payout"),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.commissions), 0).label("commissions"),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.logistics), 0).label("logistics"),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.storage), 0).label("storage"),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.ads), 0).label("ads"),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.penalties), 0).label("penalties"),
                func.avg(SkuUnitEconomicsDaily.margin_pct).label("margin_pct"),
                func.avg(SkuUnitEconomicsDaily.return_rate).label("return_rate"),
                func.avg(SkuUnitEconomicsDaily.ad_cost_ratio).label("ad_cost_ratio"),
                func.avg(SkuUnitEconomicsDaily.logistics_burden).label("logistics_burden"),
            )
            .where(*base_filters)
            .group_by(SkuUnitEconomicsDaily.sku)
        )
        stmt = stmt.order_by(sort_col.desc() if order_key != "asc" else sort_col.asc()).offset(skip).limit(limit)
        res = await self.execute_with_rls(stmt)
        integrity = await self._integrity(
            marketplace=marketplace, period=period, semantics_version=freshness.semantics_version
        )
        trust = integrity.profit_metrics_trust if integrity else "insufficient"
        items: list[SkuEconomicsRow] = []
        for r in res.all():
            cm = gate_profit_decimal(Decimal(r[2]), trust=trust or "insufficient")
            gp = gate_profit_decimal(Decimal(r[3]), trust=trust or "insufficient")
            items.append(
                SkuEconomicsRow(
                    sku=str(r[0]),
                    revenue=Decimal(r[1]),
                    contribution_margin=cm,
                    gross_profit=gp,
                    cogs=Decimal(r[4]) if trust == "full" else None,
                    returns_amount=Decimal(r[5]),
                    payout=Decimal(r[6]),
                    commissions=Decimal(r[7]),
                    logistics=Decimal(r[8]),
                    storage=Decimal(r[9]),
                    ads=Decimal(r[10]),
                    penalties=Decimal(r[11]),
                    margin_pct=gate_margin_decimal(r[12], trust=trust or "insufficient"),
                    return_rate=r[13],
                    ad_cost_ratio=r[14],
                    logistics_burden=r[15],
                )
            )

        return SkuEconomicsResponse(
            marketplace=marketplace,
            period_start=period.start,
            period_end=period.end,
            total=total,
            items=items,
            freshness=freshness,
            integrity=await self._integrity(marketplace=marketplace, period=period, semantics_version=freshness.semantics_version),
        )

    async def revenue_trend(
        self, *, marketplace: Marketplace, period: Period
    ) -> RevenueTrendResponse:
        stmt = (
            select(DailyAggregate)
            .where(DailyAggregate.marketplace == marketplace)
            .where(DailyAggregate.aggregate_date >= period.start)
            .where(DailyAggregate.aggregate_date <= period.end)
            .order_by(DailyAggregate.aggregate_date.asc())
        )
        res = await self.execute_with_rls(stmt)
        rows = list(res.scalars().all())
        integrity = await self._integrity(marketplace=marketplace, period=period)
        trust = integrity.profit_metrics_trust if integrity else "insufficient"
        points = [
            TrendPoint(
                date=r.aggregate_date,
                revenue=r.revenue,
                net_profit=gate_profit_decimal(r.net_profit, trust=trust or "insufficient"),
                margin_pct=gate_margin_decimal(r.margin, trust=trust or "insufficient"),
                units_sold=r.units_sold,
            )
            for r in rows
        ]
        return RevenueTrendResponse(
            marketplace=marketplace,
            period_start=period.start,
            period_end=period.end,
            points=points,
            freshness=await self._freshness(),
            integrity=integrity,
        )

    async def top_skus(
        self,
        *,
        marketplace: Marketplace,
        period: Period,
        limit: int,
        sort: str,
    ) -> TopSkusResponse:
        sort_key = sort.lower()
        sort_col = (
            func.sum(SkuDailyMetric.revenue)
            if sort_key == "revenue"
            else func.sum(SkuDailyMetric.net_profit)
        )

        stmt = (
            select(
                SkuDailyMetric.sku,
                func.sum(SkuDailyMetric.revenue).label("revenue"),
                func.sum(SkuDailyMetric.net_profit).label("net_profit"),
                func.sum(SkuDailyMetric.units_sold).label("units_sold"),
            )
            .where(SkuDailyMetric.marketplace == marketplace)
            .where(SkuDailyMetric.metric_date >= period.start)
            .where(SkuDailyMetric.metric_date <= period.end)
            .group_by(SkuDailyMetric.sku)
            .order_by(sort_col.desc())
            .limit(limit)
        )
        total_stmt = (
            select(func.coalesce(func.sum(SkuDailyMetric.revenue), 0))
            .where(SkuDailyMetric.marketplace == marketplace)
            .where(SkuDailyMetric.metric_date >= period.start)
            .where(SkuDailyMetric.metric_date <= period.end)
        )
        res = await self.execute_with_rls(stmt)
        total_res = await self.execute_with_rls(total_stmt)
        total_revenue = Decimal(total_res.scalar_one())

        integrity = await self._integrity(marketplace=marketplace, period=period)
        trust = integrity.profit_metrics_trust if integrity else "insufficient"

        items: list[TopSkuRow] = []
        for sku, revenue, profit, units_sold in res.all():
            margin = None
            if revenue and Decimal(revenue) > 0:
                margin = (Decimal(profit) / Decimal(revenue)) * Decimal("100")
            profit_out = gate_profit_decimal(Decimal(profit), trust=trust or "insufficient")
            margin_out = gate_margin_decimal(margin, trust=trust or "insufficient")
            contribution = (
                (Decimal(revenue) / total_revenue) * Decimal("100")
                if total_revenue > 0
                else None
            )
            items.append(
                TopSkuRow(
                    sku=str(sku),
                    revenue=Decimal(revenue),
                    net_profit=profit_out,
                    margin_pct=margin_out,
                    units_sold=int(units_sold or 0),
                    contribution_pct=contribution,
                )
            )
        return TopSkusResponse(
            marketplace=marketplace,
            period_start=period.start,
            period_end=period.end,
            sort=sort_key,
            items=items,
            freshness=await self._freshness(),
            integrity=integrity,
        )

    async def warehouse_analytics(
        self, *, snapshot_date: date, semantics_version: str = "1.0"
    ) -> WarehouseAnalyticsResponse:
        stmt = (
            select(WarehouseStockSnapshot)
            .where(WarehouseStockSnapshot.snapshot_date == snapshot_date)
            .where(WarehouseStockSnapshot.semantics_version == semantics_version)
        )
        res = await self.execute_with_rls(stmt)
        rows = list(res.scalars().all())
        items = [
            WarehouseRow(
                warehouse_name=r.warehouse_name,
                opening_stock=r.opening_stock,
                inbound_units=r.inbound_units,
                sold_units=r.sold_units,
                returned_units=r.returned_units,
                lost_units=r.lost_units,
                writeoff_units=r.writeoff_units,
                expected_closing_stock=r.expected_closing_stock,
                actual_stock=r.actual_stock,
                discrepancy_units=r.discrepancy_units,
                discrepancy_cost=r.discrepancy_cost,
                discrepancy_sale_value=r.discrepancy_sale_value,
            )
            for r in rows
        ]
        return WarehouseAnalyticsResponse(
            snapshot_date=snapshot_date,
            semantics_version=semantics_version,
            items=items,
            freshness=await self._freshness(semantics_version),
            integrity=None,
        )

    async def period_compare(
        self,
        *,
        marketplace: Marketplace,
        a: Period,
        b: Period,
    ) -> PeriodComparisonResponse:
        a_sum = await self.revenue_summary(marketplace=marketplace, period=a)
        b_sum = await self.revenue_summary(marketplace=marketplace, period=b)

        delta_rev = a_sum.kpis.total_revenue - b_sum.kpis.total_revenue
        delta_profit = a_sum.kpis.total_profit - b_sum.kpis.total_profit
        delta_margin = None
        if a_sum.kpis.margin_pct is not None and b_sum.kpis.margin_pct is not None:
            delta_margin = a_sum.kpis.margin_pct - b_sum.kpis.margin_pct
        return PeriodComparisonResponse(
            marketplace=marketplace,
            a_start=a.start,
            a_end=a.end,
            b_start=b.start,
            b_end=b.end,
            a=a_sum.kpis,
            b=b_sum.kpis,
            delta_revenue=delta_rev,
            delta_profit=delta_profit,
            delta_margin_pct=delta_margin,
            freshness=await self._freshness(),
            integrity=await self._integrity(marketplace=marketplace, period=a),
        )

    async def abc_analysis(
        self, *, marketplace: Marketplace, period: Period
    ) -> AbcAnalysisResponse:
        # ABC based on revenue contribution distribution.
        stmt = (
            select(
                SkuDailyMetric.sku,
                func.sum(SkuDailyMetric.revenue).label("revenue"),
            )
            .where(SkuDailyMetric.marketplace == marketplace)
            .where(SkuDailyMetric.metric_date >= period.start)
            .where(SkuDailyMetric.metric_date <= period.end)
            .group_by(SkuDailyMetric.sku)
            .order_by(func.sum(SkuDailyMetric.revenue).desc())
        )
        total_stmt = (
            select(func.coalesce(func.sum(SkuDailyMetric.revenue), 0))
            .where(SkuDailyMetric.marketplace == marketplace)
            .where(SkuDailyMetric.metric_date >= period.start)
            .where(SkuDailyMetric.metric_date <= period.end)
        )
        res = await self.execute_with_rls(stmt)
        total_res = await self.execute_with_rls(total_stmt)
        total_rev = Decimal(total_res.scalar_one())

        # Cumulative % thresholds: A=80%, B=95%, C=rest.
        a_rev = Decimal("0")
        b_rev = Decimal("0")
        c_rev = Decimal("0")
        a_count = b_count = c_count = 0

        cum = Decimal("0")
        for _, rev in res.all():
            rev_d = Decimal(rev)
            pct = (rev_d / total_rev) if total_rev > 0 else Decimal("0")
            cum += pct
            if cum <= Decimal("0.80"):
                a_rev += rev_d
                a_count += 1
            elif cum <= Decimal("0.95"):
                b_rev += rev_d
                b_count += 1
            else:
                c_rev += rev_d
                c_count += 1

        def _pct(x: Decimal) -> Decimal:
            return (x / total_rev) * Decimal("100") if total_rev > 0 else Decimal("0")

        buckets = [
            AbcBucketRow(bucket="A", sku_count=a_count, revenue=a_rev, revenue_pct=_pct(a_rev)),
            AbcBucketRow(bucket="B", sku_count=b_count, revenue=b_rev, revenue_pct=_pct(b_rev)),
            AbcBucketRow(bucket="C", sku_count=c_count, revenue=c_rev, revenue_pct=_pct(c_rev)),
        ]
        return AbcAnalysisResponse(
            marketplace=marketplace,
            period_start=period.start,
            period_end=period.end,
            buckets=buckets,
            freshness=await self._freshness(),
            integrity=await self._integrity(marketplace=marketplace, period=period),
        )

    async def inventory_risk(
        self, *, snapshot_date: date, semantics_version: str = "1.0"
    ) -> InventoryRiskIndicatorsResponse:
        # Simple risk indicators from warehouse snapshots.
        stmt = (
            select(
                func.count(func.distinct(WarehouseStockSnapshot.warehouse_name)),
                func.coalesce(func.sum(WarehouseStockSnapshot.discrepancy_cost), 0),
            )
            .where(WarehouseStockSnapshot.snapshot_date == snapshot_date)
            .where(WarehouseStockSnapshot.semantics_version == semantics_version)
            .where(WarehouseStockSnapshot.discrepancy_units != 0)
        )
        res = await self.execute_with_rls(stmt)
        wh_count, cost_total = res.one()
        freshness = await self._freshness(semantics_version)
        return InventoryRiskIndicatorsResponse(
            snapshot_date=snapshot_date,
            high_discrepancy_warehouses=int(wh_count or 0),
            discrepancy_cost_total=Decimal(cost_total),
            stale_data_warning=freshness.stale_data_warning,
            freshness=freshness,
            integrity=None,
        )

    async def inventory_economics(
        self,
        *,
        marketplace: Marketplace,
        period: Period,
        limit: int = 50,
        sku_query: str | None = None,
        semantics_version: str = "1.0",
    ) -> InventoryEconomicsResponse:
        freshness = await self._freshness(semantics_version)
        snapshot_date = await self._latest_snapshot_date(period_end=period.end, semantics_version=semantics_version)
        if snapshot_date is None:
            return InventoryEconomicsResponse(
                marketplace=marketplace,
                period_start=period.start,
                period_end=period.end,
                snapshot_date=None,
                total_skus=0,
                items=[],
                freshness=freshness,
                integrity=await self._integrity(marketplace=marketplace, period=period, semantics_version=freshness.semantics_version),
            )

        # Stock units as of snapshot_date.
        stock_stmt = (
            select(
                WarehouseStockSnapshot.sku,
                func.coalesce(func.sum(WarehouseStockSnapshot.actual_stock), 0).label("stock_units"),
            )
            .where(WarehouseStockSnapshot.snapshot_date == snapshot_date)
            .where(WarehouseStockSnapshot.semantics_version == semantics_version)
            .where(WarehouseStockSnapshot.sku.is_not(None))
            .group_by(WarehouseStockSnapshot.sku)
        )
        if sku_query:
            stock_stmt = stock_stmt.where(WarehouseStockSnapshot.sku.ilike(f"%{sku_query}%"))
        stock_res = await self.execute_with_rls(stock_stmt)
        stock_by_sku = {str(sku): int(units or 0) for sku, units in stock_res.all()}

        if not stock_by_sku:
            return InventoryEconomicsResponse(
                marketplace=marketplace,
                period_start=period.start,
                period_end=period.end,
                snapshot_date=snapshot_date,
                total_skus=0,
                items=[],
                freshness=freshness,
                integrity=await self._integrity(marketplace=marketplace, period=period, semantics_version=freshness.semantics_version),
            )

        # Sold units and avg stock during the period (from snapshots).
        snap_period_stmt = (
            select(
                WarehouseStockSnapshot.sku,
                func.coalesce(func.sum(WarehouseStockSnapshot.sold_units), 0).label("sold_units"),
                func.avg(WarehouseStockSnapshot.actual_stock).label("avg_stock_units"),
            )
            .where(WarehouseStockSnapshot.snapshot_date >= period.start)
            .where(WarehouseStockSnapshot.snapshot_date <= period.end)
            .where(WarehouseStockSnapshot.semantics_version == semantics_version)
            .where(WarehouseStockSnapshot.sku.is_not(None))
            .group_by(WarehouseStockSnapshot.sku)
        )
        if sku_query:
            snap_period_stmt = snap_period_stmt.where(WarehouseStockSnapshot.sku.ilike(f"%{sku_query}%"))
        snap_period_res = await self.execute_with_rls(snap_period_stmt)
        sold_avg_by_sku: dict[str, tuple[int, Decimal | None]] = {}
        for sku, sold_units, avg_stock_units in snap_period_res.all():
            sold_avg_by_sku[str(sku)] = (int(sold_units or 0), Decimal(avg_stock_units) if avg_stock_units is not None else None)

        # Last sale date for "age" / slow movers.
        last_sale_stmt = (
            select(
                WarehouseStockSnapshot.sku,
                func.max(WarehouseStockSnapshot.snapshot_date).label("last_sale_date"),
            )
            .where(WarehouseStockSnapshot.snapshot_date >= period.start)
            .where(WarehouseStockSnapshot.snapshot_date <= period.end)
            .where(WarehouseStockSnapshot.semantics_version == semantics_version)
            .where(WarehouseStockSnapshot.sku.is_not(None))
            .where(WarehouseStockSnapshot.sold_units > 0)
            .group_by(WarehouseStockSnapshot.sku)
        )
        if sku_query:
            last_sale_stmt = last_sale_stmt.where(WarehouseStockSnapshot.sku.ilike(f"%{sku_query}%"))
        last_sale_res = await self.execute_with_rls(last_sale_stmt)
        last_sale_by_sku = {str(sku): d for sku, d in last_sale_res.all()}

        unit_cost_by_sku = await self._unit_costs_as_of(as_of=snapshot_date)

        days = max((period.end - period.start).days + 1, 1)
        items: list[InventoryEconomicsRow] = []
        for sku, stock_units in stock_by_sku.items():
            sold_units, avg_stock_units = sold_avg_by_sku.get(sku, (0, None))
            turnover = compute_turnover(sold_units=sold_units, avg_stock_units=avg_stock_units, period_days=days)

            unit_cost = unit_cost_by_sku.get(sku)
            frozen_capital = (Decimal(stock_units) * unit_cost) if unit_cost is not None else None

            last_sale = last_sale_by_sku.get(sku)
            days_since_last_sale = (snapshot_date - last_sale).days if last_sale is not None else None
            stock_risk = stock_risk_label(
                stock_units=stock_units,
                sold_units=sold_units,
                period_days=days,
                days_since_last_sale=days_since_last_sale,
            )

            items.append(
                InventoryEconomicsRow(
                    sku=sku,
                    stock_units=stock_units,
                    sold_units=sold_units,
                    avg_stock_units=avg_stock_units,
                    turnover_ratio=turnover.turnover_ratio,
                    turnover_days=turnover.turnover_days,
                    frozen_capital=frozen_capital,
                    unit_cost=unit_cost,
                    days_since_last_sale=days_since_last_sale,
                    stock_risk=stock_risk,
                )
            )

        # Sort: most frozen capital first.
        items.sort(key=lambda r: (r.frozen_capital or Decimal("-1")), reverse=True)
        items = items[:limit]

        return InventoryEconomicsResponse(
            marketplace=marketplace,
            period_start=period.start,
            period_end=period.end,
            snapshot_date=snapshot_date,
            total_skus=len(stock_by_sku),
            items=items,
            freshness=freshness,
            integrity=await self._integrity(marketplace=marketplace, period=period, semantics_version=freshness.semantics_version),
        )

    async def inventory_slow_movers(
        self,
        *,
        marketplace: Marketplace,
        period: Period,
        threshold_days: int = 30,
        limit: int = 50,
        semantics_version: str = "1.0",
    ) -> InventorySlowMoversResponse:
        freshness = await self._freshness(semantics_version)
        snapshot_date = await self._latest_snapshot_date(period_end=period.end, semantics_version=semantics_version)
        if snapshot_date is None:
            return InventorySlowMoversResponse(
                marketplace=marketplace,
                period_start=period.start,
                period_end=period.end,
                snapshot_date=None,
                threshold_days=threshold_days,
                items=[],
                freshness=freshness,
                integrity=await self._integrity(marketplace=marketplace, period=period, semantics_version=freshness.semantics_version),
            )

        unit_cost_by_sku = await self._unit_costs_as_of(as_of=snapshot_date)

        stock_stmt = (
            select(
                WarehouseStockSnapshot.sku,
                func.coalesce(func.sum(WarehouseStockSnapshot.actual_stock), 0).label("stock_units"),
            )
            .where(WarehouseStockSnapshot.snapshot_date == snapshot_date)
            .where(WarehouseStockSnapshot.semantics_version == semantics_version)
            .where(WarehouseStockSnapshot.sku.is_not(None))
            .group_by(WarehouseStockSnapshot.sku)
        )
        stock_res = await self.execute_with_rls(stock_stmt)
        stock_by_sku = {str(sku): int(units or 0) for sku, units in stock_res.all() if int(units or 0) > 0}

        last_sale_stmt = (
            select(
                WarehouseStockSnapshot.sku,
                func.max(WarehouseStockSnapshot.snapshot_date).label("last_sale_date"),
            )
            .where(WarehouseStockSnapshot.snapshot_date >= period.start)
            .where(WarehouseStockSnapshot.snapshot_date <= period.end)
            .where(WarehouseStockSnapshot.semantics_version == semantics_version)
            .where(WarehouseStockSnapshot.sku.is_not(None))
            .where(WarehouseStockSnapshot.sold_units > 0)
            .group_by(WarehouseStockSnapshot.sku)
        )
        last_sale_res = await self.execute_with_rls(last_sale_stmt)
        last_sale_by_sku = {str(sku): d for sku, d in last_sale_res.all()}

        items: list[InventorySlowMoverRow] = []
        for sku, stock_units in stock_by_sku.items():
            last_sale = last_sale_by_sku.get(sku)
            days_since_last_sale = days_since(as_of=snapshot_date, last_event=last_sale, fallback_start=period.start)
            if days_since_last_sale is None:
                continue
            if days_since_last_sale < threshold_days:
                continue
            unit_cost = unit_cost_by_sku.get(sku)
            frozen = (Decimal(stock_units) * unit_cost) if unit_cost is not None else None
            items.append(
                InventorySlowMoverRow(
                    sku=sku,
                    stock_units=stock_units,
                    frozen_capital=frozen,
                    unit_cost=unit_cost,
                    days_since_last_sale=days_since_last_sale,
                )
            )
        items.sort(key=lambda r: (r.frozen_capital or Decimal("-1")), reverse=True)
        items = items[:limit]

        return InventorySlowMoversResponse(
            marketplace=marketplace,
            period_start=period.start,
            period_end=period.end,
            snapshot_date=snapshot_date,
            threshold_days=threshold_days,
            items=items,
            freshness=freshness,
            integrity=await self._integrity(marketplace=marketplace, period=period, semantics_version=freshness.semantics_version),
        )

    async def inventory_dead_stock(
        self,
        *,
        marketplace: Marketplace,
        period: Period,
        threshold_days: int = 60,
        limit: int = 50,
        semantics_version: str = "1.0",
    ) -> InventoryDeadStockResponse:
        freshness = await self._freshness(semantics_version)
        snapshot_date = await self._latest_snapshot_date(period_end=period.end, semantics_version=semantics_version)
        if snapshot_date is None:
            return InventoryDeadStockResponse(
                marketplace=marketplace,
                period_start=period.start,
                period_end=period.end,
                snapshot_date=None,
                threshold_days=threshold_days,
                items=[],
                freshness=freshness,
                integrity=await self._integrity(marketplace=marketplace, period=period, semantics_version=freshness.semantics_version),
            )

        unit_cost_by_sku = await self._unit_costs_as_of(as_of=snapshot_date)

        stock_stmt = (
            select(
                WarehouseStockSnapshot.sku,
                func.coalesce(func.sum(WarehouseStockSnapshot.actual_stock), 0).label("stock_units"),
            )
            .where(WarehouseStockSnapshot.snapshot_date == snapshot_date)
            .where(WarehouseStockSnapshot.semantics_version == semantics_version)
            .where(WarehouseStockSnapshot.sku.is_not(None))
            .group_by(WarehouseStockSnapshot.sku)
        )
        stock_res = await self.execute_with_rls(stock_stmt)
        stock_by_sku = {str(sku): int(units or 0) for sku, units in stock_res.all() if int(units or 0) > 0}

        last_sale_stmt = (
            select(
                WarehouseStockSnapshot.sku,
                func.max(WarehouseStockSnapshot.snapshot_date).label("last_sale_date"),
            )
            .where(WarehouseStockSnapshot.snapshot_date >= period.start)
            .where(WarehouseStockSnapshot.snapshot_date <= period.end)
            .where(WarehouseStockSnapshot.semantics_version == semantics_version)
            .where(WarehouseStockSnapshot.sku.is_not(None))
            .where(WarehouseStockSnapshot.sold_units > 0)
            .group_by(WarehouseStockSnapshot.sku)
        )
        last_sale_res = await self.execute_with_rls(last_sale_stmt)
        last_sale_by_sku = {str(sku): d for sku, d in last_sale_res.all()}

        items: list[InventoryDeadStockRow] = []
        for sku, stock_units in stock_by_sku.items():
            last_sale = last_sale_by_sku.get(sku)
            days_since_last_sale = days_since(as_of=snapshot_date, last_event=last_sale, fallback_start=period.start)
            if days_since_last_sale is None:
                continue
            if days_since_last_sale < threshold_days:
                continue
            unit_cost = unit_cost_by_sku.get(sku)
            frozen = (Decimal(stock_units) * unit_cost) if unit_cost is not None else None
            items.append(
                InventoryDeadStockRow(
                    sku=sku,
                    stock_units=stock_units,
                    frozen_capital=frozen,
                    unit_cost=unit_cost,
                    days_since_last_sale=days_since_last_sale,
                )
            )
        items.sort(key=lambda r: (r.frozen_capital or Decimal("-1")), reverse=True)
        items = items[:limit]

        return InventoryDeadStockResponse(
            marketplace=marketplace,
            period_start=period.start,
            period_end=period.end,
            snapshot_date=snapshot_date,
            threshold_days=threshold_days,
            items=items,
            freshness=freshness,
            integrity=await self._integrity(marketplace=marketplace, period=period, semantics_version=freshness.semantics_version),
        )

    async def sku_drilldown(
        self,
        *,
        marketplace: Marketplace,
        sku: str,
        period: Period,
        semantics_version: str = "1.0",
    ) -> SkuDrilldownResponse:
        freshness = await self._freshness(semantics_version)

        econ_stmt = (
            select(SkuUnitEconomicsDaily)
            .where(SkuUnitEconomicsDaily.marketplace == marketplace)
            .where(SkuUnitEconomicsDaily.sku == sku)
            .where(SkuUnitEconomicsDaily.metric_date >= period.start)
            .where(SkuUnitEconomicsDaily.metric_date <= period.end)
            .order_by(SkuUnitEconomicsDaily.metric_date.asc())
        )
        econ_res = await self.execute_with_rls(econ_stmt)
        econ_rows = list(econ_res.scalars().all())

        # Best-effort stock series (total actual_stock per day across warehouses).
        stock_stmt = (
            select(
                WarehouseStockSnapshot.snapshot_date,
                func.coalesce(func.sum(WarehouseStockSnapshot.actual_stock), 0).label("stock_units"),
            )
            .where(WarehouseStockSnapshot.sku == sku)
            .where(WarehouseStockSnapshot.snapshot_date >= period.start)
            .where(WarehouseStockSnapshot.snapshot_date <= period.end)
            .where(WarehouseStockSnapshot.semantics_version == semantics_version)
            .group_by(WarehouseStockSnapshot.snapshot_date)
            .order_by(WarehouseStockSnapshot.snapshot_date.asc())
        )
        stock_res = await self.execute_with_rls(stock_stmt)
        stock_by_day = {d: int(u or 0) for d, u in stock_res.all()}

        points: list[SkuEconomicsTrendPoint] = []
        for r in econ_rows:
            points.append(
                SkuEconomicsTrendPoint(
                    date=r.metric_date,
                    revenue=r.revenue,
                    gross_profit=r.gross_profit,
                    contribution_margin=r.contribution_margin,
                    margin_pct=r.margin_pct,
                    returns_amount=r.returns_amount,
                    logistics=r.logistics,
                    ads=r.ads,
                    penalties=r.penalties,
                    payout=r.payout,
                    stock_units=stock_by_day.get(r.metric_date),
                )
            )

        return SkuDrilldownResponse(
            marketplace=marketplace,
            sku=sku,
            period_start=period.start,
            period_end=period.end,
            points=points,
            freshness=freshness,
            integrity=await self._integrity(marketplace=marketplace, period=period, semantics_version=freshness.semantics_version),
        )


def _compute_missing_ranges(days_sorted: list[date], *, limit_ranges: int = 50) -> list[MissingPeriodRange]:
    """
    Convert an ordered list of available days into missing date ranges.
    Uses inclusive start/end for missing segments.
    """
    if not days_sorted:
        return []
    missing: list[MissingPeriodRange] = []
    prev = days_sorted[0]
    for cur in days_sorted[1:]:
        delta = (cur - prev).days
        if delta > 1:
            start = date.fromordinal(prev.toordinal() + 1)
            end = date.fromordinal(cur.toordinal() - 1)
            missing_days = (end - start).days + 1
            missing.append(MissingPeriodRange(start=start, end=end, missing_days=missing_days))
            if len(missing) >= limit_ranges:
                break
        prev = cur
    return missing

