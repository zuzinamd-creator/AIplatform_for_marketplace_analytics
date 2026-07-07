"""Profit after manual promotion expenses (read-layer overlay)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PromotionAdjustedProfit:
    settlement_wb: Decimal
    promotion_expenses: Decimal
    adjusted_settlement: Decimal
    cogs: Decimal
    seller_profit_raw: Decimal
    seller_profit_after_promotion: Decimal
    margin_pct: Decimal | None
    profitability_pct: Decimal | None
    margin_pct_raw: Decimal | None
    profitability_pct_raw: Decimal | None


def compute_promotion_impact_pct(
    *,
    seller_profit_raw: Decimal,
    seller_profit_after_promotion: Decimal,
) -> Decimal | None:
    """Share of settlement profit consumed by promotion: (raw - after) * 100 / raw."""
    if seller_profit_raw <= 0:
        return None
    return (seller_profit_raw - seller_profit_after_promotion) * Decimal("100") / seller_profit_raw


def compute_profit_after_promotion(
    *,
    settlement_wb: Decimal,
    promotion_expenses: Decimal,
    cogs: Decimal,
    revenue: Decimal,
) -> PromotionAdjustedProfit:
    """
    Settlement WB = total_to_pay from marketplace.
    seller_profit_raw = settlement_wb - COGS
    seller_profit_after_promotion = (settlement_wb - promotion_expenses) - COGS
    """
    adjusted_settlement = settlement_wb - promotion_expenses
    seller_profit_raw = settlement_wb - cogs
    seller_profit_after_promotion = adjusted_settlement - cogs
    margin_pct_raw = (
        (seller_profit_raw / revenue * Decimal("100")) if revenue > 0 else None
    )
    profitability_pct_raw = (
        (seller_profit_raw / cogs * Decimal("100")) if cogs > 0 else None
    )
    margin_pct = (
        (seller_profit_after_promotion / revenue * Decimal("100"))
        if revenue > 0
        else None
    )
    profitability_pct = (
        (seller_profit_after_promotion / cogs * Decimal("100")) if cogs > 0 else None
    )
    return PromotionAdjustedProfit(
        settlement_wb=settlement_wb,
        promotion_expenses=promotion_expenses,
        adjusted_settlement=adjusted_settlement,
        cogs=cogs,
        seller_profit_raw=seller_profit_raw,
        seller_profit_after_promotion=seller_profit_after_promotion,
        margin_pct=margin_pct,
        profitability_pct=profitability_pct,
        margin_pct_raw=margin_pct_raw,
        profitability_pct_raw=profitability_pct_raw,
    )
