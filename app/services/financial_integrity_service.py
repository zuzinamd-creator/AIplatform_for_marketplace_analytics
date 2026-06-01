"""Deterministic financial integrity checks (tenant-scoped, read-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select

from app.models.cost_history import CostHistory
from app.models.finance.aggregates import DailyAggregate
from app.models.finance.reconciliation import ReportReconciliation
from app.models.report import Marketplace
from app.schemas.analytics import AnalyticsIntegrityMeta, IntegrityWarning
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
                    message="Negative revenue detected for the selected period (check normalization signs and returns).",
                    context={"marketplace": marketplace.value},
                )
            )

        if revenue >= 0 and profit > revenue:
            warnings.append(
                IntegrityWarning(
                    code="profit_gt_revenue",
                    severity="critical",
                    message="Profit exceeds revenue for the selected period (financially impossible).",
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
                        message="Abnormal margin detected (outside [-100%; 100%]). Check duplicated aggregation or sign errors.",
                        context={
                            "marketplace": marketplace.value,
                            "margin_pct": str(margin.quantize(Decimal("0.01"))),
                        },
                    )
                )

        # Missing cost basis warning (profitability completeness).
        # Heuristic: if tenant has no cost history, profit/margin are not financially governed.
        cost_stmt = select(func.count(CostHistory.id))
        cost_res = await self.execute_with_rls(cost_stmt)
        has_costs = int(cost_res.scalar_one() or 0) > 0
        if not has_costs and revenue != 0:
            warnings.append(
                IntegrityWarning(
                    code="missing_cost_basis",
                    severity="warning",
                    message="No cost history detected; profit and margin may be overstated (COGS assumed 0). Upload costs to enable governed gross profit.",
                    context={"marketplace": marketplace.value},
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
                    message="Payout reconciliation mismatches detected between expected and actual payouts (check returns/fees sign mapping).",
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
        )

