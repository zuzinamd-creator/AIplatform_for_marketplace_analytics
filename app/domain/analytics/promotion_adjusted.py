"""Manual expense context for WB promotion / Jam (read-layer annotation).

Phase 9.9-R15 Variant A:
  Manual expenses (promotion / jam) are breakdown of WB deductions already
  included in settlement. They must NOT be subtracted again from profit.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PromotionAdjustedProfit:
    settlement_wb: Decimal
    wb_promotion_expenses: Decimal
    jam_subscription_expenses: Decimal
    manual_expenses_total: Decimal
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
    """
    Legacy diagnostic: share of settlement profit that would disappear under
    a second manual subtract. Under Variant A primary profit equals raw, so
    impact is omitted (None) unless values diverge.
    """
    if seller_profit_raw <= 0:
        return None
    if seller_profit_after_promotion == seller_profit_raw:
        return None
    return (seller_profit_raw - seller_profit_after_promotion) * Decimal("100") / seller_profit_raw


def compute_profit_after_promotion(
    *,
    settlement_wb: Decimal,
    wb_promotion_expenses: Decimal,
    jam_subscription_expenses: Decimal = Decimal("0"),
    cogs: Decimal,
    revenue: Decimal,
) -> PromotionAdjustedProfit:
    """
    Variant A (Phase 9.9-R15):

      seller_profit = settlement_wb − COGS
      promotion / jam = display / deduction breakdown only (no second subtract)

    Compatibility fields:
      adjusted_settlement == settlement_wb
      seller_profit_after_promotion == seller_profit_raw
      margin_pct / profitability_pct computed on primary settlement profit
    """
    manual_expenses_total = wb_promotion_expenses + jam_subscription_expenses
    # No second subtract — deductions already reduced settlement_wb.
    adjusted_settlement = settlement_wb
    seller_profit_raw = settlement_wb - cogs
    seller_profit_after_promotion = seller_profit_raw
    margin_pct_raw = (
        (seller_profit_raw / revenue * Decimal("100")) if revenue > 0 else None
    )
    profitability_pct_raw = (
        (seller_profit_raw / cogs * Decimal("100")) if cogs > 0 else None
    )
    margin_pct = margin_pct_raw
    profitability_pct = profitability_pct_raw
    return PromotionAdjustedProfit(
        settlement_wb=settlement_wb,
        wb_promotion_expenses=wb_promotion_expenses,
        jam_subscription_expenses=jam_subscription_expenses,
        manual_expenses_total=manual_expenses_total,
        adjusted_settlement=adjusted_settlement,
        cogs=cogs,
        seller_profit_raw=seller_profit_raw,
        seller_profit_after_promotion=seller_profit_after_promotion,
        margin_pct=margin_pct,
        profitability_pct=profitability_pct,
        margin_pct_raw=margin_pct_raw,
        profitability_pct_raw=profitability_pct_raw,
    )
