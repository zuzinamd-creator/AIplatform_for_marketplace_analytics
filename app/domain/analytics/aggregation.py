from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.finance.types import LedgerEntryDraft, SkuCostSnapshot
from app.models.finance.enums import LedgerOperationType
from app.models.report import Marketplace


@dataclass(frozen=True)
class DailyAggregateDraft:
    aggregate_date: date
    marketplace: Marketplace
    revenue: Decimal
    net_profit: Decimal
    margin: Decimal | None
    roi: Decimal | None
    return_rate: Decimal | None
    buyout_rate: Decimal | None
    average_check: Decimal | None
    units_sold: int


@dataclass(frozen=True)
class SkuDailyMetricDraft:
    sku: str
    metric_date: date
    marketplace: Marketplace
    revenue: Decimal
    net_profit: Decimal
    margin: Decimal | None
    roi: Decimal | None
    return_rate: Decimal | None
    buyout_rate: Decimal | None
    average_check: Decimal | None
    units_sold: int


class AggregationEngine:
    """Materialized profitability metrics from ledger + historical costs."""

    @staticmethod
    def build(
        entries: list[LedgerEntryDraft],
        *,
        marketplace: Marketplace,
        costs_by_sku: dict[str, list[SkuCostSnapshot]],
        default_date: date,
    ) -> tuple[list[DailyAggregateDraft], list[SkuDailyMetricDraft]]:
        by_day: dict[date, list[LedgerEntryDraft]] = {}
        by_day_sku: dict[tuple[date, str], list[LedgerEntryDraft]] = {}

        for entry in entries:
            day = entry.operation_date or default_date
            by_day.setdefault(day, []).append(entry)
            if entry.sku:
                by_day_sku.setdefault((day, entry.sku), []).append(entry)

        daily: list[DailyAggregateDraft] = []
        sku_metrics: list[SkuDailyMetricDraft] = []

        for day, day_entries in sorted(by_day.items()):
            revenue = AggregationEngine._sum_sales(day_entries)
            cogs = AggregationEngine._sum_cogs(day_entries, costs_by_sku)
            profit = AggregationEngine._net_amount(day_entries) - cogs
            units = AggregationEngine._units_sold(day_entries)
            returns = AggregationEngine._returns(day_entries)
            margin = (profit / revenue * Decimal("100")) if revenue > Decimal("0") else None
            roi = (profit / cogs * Decimal("100")) if cogs > Decimal("0") else None
            return_rate = (returns / revenue * Decimal("100")) if revenue > Decimal("0") else None
            avg_check = revenue / Decimal(units) if units > 0 else None
            daily.append(
                DailyAggregateDraft(
                    aggregate_date=day,
                    marketplace=marketplace,
                    revenue=revenue,
                    net_profit=profit,
                    margin=margin,
                    roi=roi,
                    return_rate=return_rate,
                    buyout_rate=None,
                    average_check=avg_check,
                    units_sold=units,
                )
            )

        for (day, sku), sku_entries in sorted(by_day_sku.items()):
            revenue = AggregationEngine._sum_sales(sku_entries)
            cogs = AggregationEngine._sum_cogs(sku_entries, costs_by_sku)
            profit = AggregationEngine._net_amount(sku_entries) - cogs
            units = AggregationEngine._units_sold(sku_entries)
            returns = AggregationEngine._returns(sku_entries)
            margin = (profit / revenue * Decimal("100")) if revenue > Decimal("0") else None
            roi = (profit / cogs * Decimal("100")) if cogs > Decimal("0") else None
            return_rate = (returns / revenue * Decimal("100")) if revenue > Decimal("0") else None
            avg_check = revenue / Decimal(units) if units > 0 else None
            sku_metrics.append(
                SkuDailyMetricDraft(
                    sku=sku,
                    metric_date=day,
                    marketplace=marketplace,
                    revenue=revenue,
                    net_profit=profit,
                    margin=margin,
                    roi=roi,
                    return_rate=return_rate,
                    buyout_rate=None,
                    average_check=avg_check,
                    units_sold=units,
                )
            )
        return daily, sku_metrics

    @staticmethod
    def _sum_sales(entries: list[LedgerEntryDraft]) -> Decimal:
        return sum(
            (e.amount for e in entries if e.operation_type == LedgerOperationType.SALE),
            start=Decimal("0"),
        )

    @staticmethod
    def _returns(entries: list[LedgerEntryDraft]) -> Decimal:
        return sum(
            (abs(e.amount) for e in entries if e.operation_type == LedgerOperationType.RETURN),
            start=Decimal("0"),
        )

    @staticmethod
    def _net_amount(entries: list[LedgerEntryDraft]) -> Decimal:
        # Profit is P&L-oriented, not cashflow-oriented: exclude PAYOUT to avoid
        # double-counting seller cash movements inside net profit.
        return sum(
            (e.amount for e in entries if e.operation_type != LedgerOperationType.PAYOUT),
            start=Decimal("0"),
        )

    @staticmethod
    def _units_sold(entries: list[LedgerEntryDraft]) -> int:
        return sum(1 for e in entries if e.operation_type == LedgerOperationType.SALE and e.amount > 0)

    @staticmethod
    def _sum_cogs(entries: list[LedgerEntryDraft], costs: dict[str, list[SkuCostSnapshot]]) -> Decimal:
        total = Decimal("0")
        for entry in entries:
            if entry.operation_type != LedgerOperationType.SALE or not entry.sku:
                continue
            unit_cost = AggregationEngine._cost_on_date(costs.get(entry.sku, []), entry.operation_date)
            if unit_cost is not None:
                total += unit_cost
        return total

    @staticmethod
    def _cost_on_date(history: list[SkuCostSnapshot], on_date: date) -> Decimal | None:
        applicable = [item for item in history if item.effective_from <= on_date]
        if not applicable:
            return None
        latest = max(applicable, key=lambda item: item.effective_from)
        return latest.total_unit_cost
