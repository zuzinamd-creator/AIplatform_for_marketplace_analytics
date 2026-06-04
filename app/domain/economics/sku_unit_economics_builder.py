"""Deterministic SKU unit economics from ledger drafts + effective-dated costs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.finance.types import LedgerEntryDraft, SkuCostSnapshot
from app.models.finance.enums import LedgerOperationType
from app.models.report import Marketplace


@dataclass(frozen=True)
class SkuUnitEconomicsDraft:
    sku: str
    metric_date: date
    marketplace: Marketplace
    units_sold: int
    revenue: Decimal
    returns_amount: Decimal
    payout: Decimal
    commissions: Decimal
    logistics: Decimal
    storage: Decimal
    ads: Decimal
    penalties: Decimal
    acquiring: Decimal
    deductions: Decimal
    compensation: Decimal
    cogs: Decimal
    gross_profit: Decimal
    contribution_margin: Decimal
    margin_pct: Decimal | None
    return_rate: Decimal | None
    ad_cost_ratio: Decimal | None
    logistics_burden: Decimal | None


class SkuUnitEconomicsBuilder:
    @staticmethod
    def build(
        entries: list[LedgerEntryDraft],
        *,
        marketplace: Marketplace,
        costs_by_sku: dict[str, list[SkuCostSnapshot]],
        affected_dates: set[date] | None = None,
    ) -> list[SkuUnitEconomicsDraft]:
        by_day_sku: dict[tuple[date, str], list[LedgerEntryDraft]] = {}
        for entry in entries:
            if not entry.sku:
                continue
            day = entry.operation_date
            if affected_dates is not None and day not in affected_dates:
                continue
            by_day_sku.setdefault((day, entry.sku), []).append(entry)

        rows: list[SkuUnitEconomicsDraft] = []
        for (metric_date, sku), sku_entries in sorted(by_day_sku.items()):
            rows.append(
                SkuUnitEconomicsBuilder._compute_row(
                    sku=sku,
                    metric_date=metric_date,
                    marketplace=marketplace,
                    rows=sku_entries,
                    costs_by_sku=costs_by_sku,
                )
            )
        return rows

    @staticmethod
    def _compute_row(
        *,
        sku: str,
        metric_date: date,
        marketplace: Marketplace,
        rows: list[LedgerEntryDraft],
        costs_by_sku: dict[str, list[SkuCostSnapshot]],
    ) -> SkuUnitEconomicsDraft:
        sums: dict[LedgerOperationType, Decimal] = {}
        units_sold = 0
        for row in rows:
            op = row.operation_type
            sums[op] = sums.get(op, Decimal("0")) + Decimal(row.amount)
            if op == LedgerOperationType.SALE and Decimal(row.amount) > 0:
                units_sold += 1

        revenue = sums.get(LedgerOperationType.SALE, Decimal("0"))
        returns_amount = abs(sums.get(LedgerOperationType.RETURN, Decimal("0")))
        payout = sums.get(LedgerOperationType.PAYOUT, Decimal("0"))
        commissions = abs(sums.get(LedgerOperationType.COMMISSION, Decimal("0")))
        logistics = abs(sums.get(LedgerOperationType.LOGISTICS, Decimal("0")))
        storage = abs(sums.get(LedgerOperationType.STORAGE_FEE, Decimal("0")))
        ads = abs(sums.get(LedgerOperationType.ADVERTISEMENT, Decimal("0")))
        penalties = abs(sums.get(LedgerOperationType.PENALTY, Decimal("0")))
        acquiring = abs(sums.get(LedgerOperationType.ACQUIRING, Decimal("0")))
        deductions = abs(sums.get(LedgerOperationType.DEDUCTION, Decimal("0")))
        compensation = sums.get(LedgerOperationType.COMPENSATION, Decimal("0"))

        unit_cost = SkuUnitEconomicsBuilder._unit_cost_on_date(costs_by_sku.get(sku, []), metric_date)
        cogs = (unit_cost * Decimal(units_sold)) if unit_cost is not None else Decimal("0")

        gross_profit = (revenue - returns_amount) + compensation
        contribution_margin = (
            gross_profit
            - commissions
            - logistics
            - storage
            - ads
            - penalties
            - acquiring
            - deductions
            - cogs
        )

        margin_pct = (contribution_margin / revenue * Decimal("100")) if revenue > 0 else None
        return_rate = (returns_amount / revenue * Decimal("100")) if revenue > 0 else None
        ad_cost_ratio = (ads / revenue * Decimal("100")) if revenue > 0 else None
        logistics_burden = (logistics / revenue * Decimal("100")) if revenue > 0 else None

        return SkuUnitEconomicsDraft(
            sku=sku,
            metric_date=metric_date,
            marketplace=marketplace,
            units_sold=units_sold,
            revenue=revenue,
            returns_amount=returns_amount,
            payout=payout,
            commissions=commissions,
            logistics=logistics,
            storage=storage,
            ads=ads,
            penalties=penalties,
            acquiring=acquiring,
            deductions=deductions,
            compensation=compensation,
            cogs=cogs,
            gross_profit=gross_profit,
            contribution_margin=contribution_margin,
            margin_pct=margin_pct,
            return_rate=return_rate,
            ad_cost_ratio=ad_cost_ratio,
            logistics_burden=logistics_burden,
        )

    @staticmethod
    def _unit_cost_on_date(history: list[SkuCostSnapshot], on_date: date) -> Decimal | None:
        applicable = [item for item in history if item.effective_from <= on_date]
        if not applicable:
            return None
        latest = max(applicable, key=lambda item: item.effective_from)
        return latest.total_unit_cost
