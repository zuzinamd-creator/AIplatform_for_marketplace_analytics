"""Deterministic financial integrity checks (tenant-scoped, read-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.domain.finance.cost_lookup import resolve_cost_snapshots, unit_cost_on_date
from app.etl.wb.persist_aggregates import WbPersistAggregatesMixin
from app.models.cost_history import CostHistory
from app.models.economics.sku_unit_economics import SkuUnitEconomicsDaily
from app.models.finance.aggregates import DailyAggregate
from app.models.finance.reconciliation import ReportReconciliation
from app.models.report import Marketplace
from app.schemas.analytics import AnalyticsIntegrityMeta, IntegrityWarning
from app.domain.analytics.profit_trust import classify_profit_trust
from app.services.base import TenantScopedService


@dataclass(frozen=True)
class IntegrityPeriod:
    start: date
    end: date


class FinancialIntegrityService(TenantScopedService):
    """
    Seller-facing integrity validator.

    Rules:
    - deterministic
    - tenant-scoped (RLS)
    - read-only (SELECT-only)
    - derived only from governed ledgers/projections
    """

    async def validate_period(
        self,
        *,
        marketplace: Marketplace,
        period: IntegrityPeriod,
        semantics_version: str = "1.0",
    ) -> AnalyticsIntegrityMeta:
        warnings: list[IntegrityWarning] = []

        # Aggregate-level sanity for the selected period.
        stmt = (
            select(
                func.coalesce(func.sum(DailyAggregate.revenue), 0),
                func.coalesce(func.sum(DailyAggregate.net_profit), 0),
                func.min(DailyAggregate.aggregate_date),
                func.max(DailyAggregate.aggregate_date),
                func.count(DailyAggregate.aggregate_date),
            )
            .where(DailyAggregate.marketplace == marketplace)
            .where(DailyAggregate.aggregate_date >= period.start)
            .where(DailyAggregate.aggregate_date <= period.end)
        )
        res = await self.execute_with_rls(stmt)
        revenue_sum, profit_sum, min_date, max_date, day_rows = res.one()

        revenue = Decimal(revenue_sum)
        profit = Decimal(profit_sum)

        if revenue < 0:
            warnings.append(
                IntegrityWarning(
                    code="negative_revenue",
                    severity="critical",
                    message="Отрицательная выручка за период — проверьте знаки и возвраты в отчёте.",
                    context={"marketplace": marketplace.value},
                )
            )

        if revenue >= 0 and profit > revenue:
            warnings.append(
                IntegrityWarning(
                    code="profit_gt_revenue",
                    severity="critical",
                    message="Прибыль больше выручки — финансово невозможно, проверьте агрегацию.",
                    context={
                        "marketplace": marketplace.value,
                        "revenue": str(revenue),
                        "profit": str(profit),
                        "semantics_version": semantics_version,
                    },
                )
            )

        if revenue > 0:
            margin = (profit / revenue) * Decimal("100")
            if margin < Decimal("-100") or margin > Decimal("100"):
                warnings.append(
                    IntegrityWarning(
                        code="abnormal_margin",
                        severity="warning",
                        message="Аномальная маржа (вне диапазона −100%…100%) — возможны дубли или ошибка знаков.",
                        context={
                            "marketplace": marketplace.value,
                            "margin_pct": str(margin.quantize(Decimal("0.01"))),
                        },
                    )
                )

        cost_stmt = select(func.count(CostHistory.id))
        cost_res = await self.execute_with_rls(cost_stmt)
        has_costs = int(cost_res.scalar_one() or 0) > 0
        if not has_costs and revenue != 0:
            warnings.append(
                IntegrityWarning(
                    code="missing_cost_basis",
                    severity="warning",
                    message="Себестоимость не загружена — прибыль и маржа могут быть завышены.",
                    context={"marketplace": marketplace.value},
                )
            )

        sku_cost_coverage_pct = await self._sku_cost_coverage_pct(
            marketplace=marketplace,
            period=period,
        )
        profit_metrics_trust = classify_profit_trust(sku_cost_coverage_pct)
        if profit_metrics_trust == "insufficient" and revenue != 0:
            warnings.append(
                IntegrityWarning(
                    code="profit_kpi_suppressed",
                    severity="warning",
                    message="Прибыль и маржа скрыты: у проданных товаров не указана себестоимость (или покрытие 0%).",
                    context={
                        "sku_cost_coverage_pct": str(sku_cost_coverage_pct or 0),
                        "profit_metrics_trust": profit_metrics_trust,
                    },
                )
            )
        elif profit_metrics_trust == "partial":
            warnings.append(
                IntegrityWarning(
                    code="partial_cost_coverage",
                    severity="warning",
                    message="Маржа скрыта: себестоимость указана не для всех проданных SKU — прибыль может быть неточной.",
                    context={
                        "sku_cost_coverage_pct": str(sku_cost_coverage_pct or 0),
                        "profit_metrics_trust": profit_metrics_trust,
                    },
                )
            )

        # Payout reconciliation drift (report-level, best-effort).
        # This is not period-filtered (reconciliation is per report), but it signals normalization integrity issues.
        rec_stmt = select(
            func.coalesce(func.sum(func.abs(ReportReconciliation.difference)), 0),
            func.count(ReportReconciliation.id),
        )
        rec_res = await self.execute_with_rls(rec_stmt)
        diff_abs_sum, rec_count = rec_res.one()
        diff_abs_sum_d = Decimal(diff_abs_sum)
        if int(rec_count or 0) > 0 and diff_abs_sum_d > Decimal("0"):
            warnings.append(
                IntegrityWarning(
                    code="payout_reconciliation_mismatch",
                    severity="warning",
                    message="Есть расхождение выплат: проверьте возвраты, комиссии и знаки сумм в отчёте.",
                    context={"absolute_difference_sum": str(diff_abs_sum_d), "reports": str(int(rec_count or 0))},
                )
            )

        # Very small completeness score heuristic (kept simple & deterministic).
        # 100 = costs exist and we have at least one aggregate day for this period.
        completeness: Decimal | None = None
        if day_rows and int(day_rows) > 0:
            completeness = Decimal("100")
            if not has_costs:
                completeness -= Decimal("35")
            if warnings and any(w.severity == "critical" for w in warnings):
                completeness -= Decimal("40")
            completeness = max(Decimal("0"), min(Decimal("100"), completeness))

        return AnalyticsIntegrityMeta(
            warnings=warnings,
            financial_completeness_score=completeness,
            sku_cost_coverage_pct=sku_cost_coverage_pct,
            profit_metrics_trust=profit_metrics_trust,
        )

    async def _sku_cost_coverage_pct(
        self,
        *,
        marketplace: Marketplace,
        period: IntegrityPeriod,
    ) -> Decimal | None:
        filters = [
            SkuUnitEconomicsDaily.marketplace == marketplace,
            SkuUnitEconomicsDaily.metric_date >= period.start,
            SkuUnitEconomicsDaily.metric_date <= period.end,
        ]
        selling_stmt = (
            select(SkuUnitEconomicsDaily.sku)
            .where(*filters)
            .where(SkuUnitEconomicsDaily.units_sold > 0)
            .group_by(SkuUnitEconomicsDaily.sku)
        )
        selling_res = await self.execute_with_rls(selling_stmt)
        selling_skus = [str(row[0]) for row in selling_res.all() if row[0]]
        if not selling_skus:
            return None

        if self.user_id is None:
            return None
        async with self._rls_transaction():
            cost_lookup = await WbPersistAggregatesMixin.load_cost_snapshots(self.db, self.user_id)
        covered = 0
        for sku in selling_skus:
            history = resolve_cost_snapshots(cost_lookup, sku)
            if unit_cost_on_date(history, period.end) is not None:
                covered += 1
        return (Decimal(covered) / Decimal(len(selling_skus)) * Decimal("100")).quantize(Decimal("0.01"))

