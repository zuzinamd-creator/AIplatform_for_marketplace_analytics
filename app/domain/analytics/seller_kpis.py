"""Seller-facing settlement KPIs (cash-based, WB report semantics)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class SellerKpis:
    revenue: Decimal
    payout_for_goods: Decimal
    logistics: Decimal
    storage: Decimal
    deductions: Decimal
    total_to_pay: Decimal
    cogs: Decimal
    seller_profit: Decimal
    margin_pct: Decimal | None
    profitability_pct: Decimal | None


def compute_seller_kpis(
    *,
    revenue: Decimal,
    payout_sales: Decimal,
    payout_returns: Decimal,
    logistics: Decimal,
    storage: Decimal,
    deductions: Decimal,
    cogs: Decimal,
) -> SellerKpis:
    """
    Seller settlement model:
      payout_for_goods = payout_sales - payout_returns
      total_to_pay = payout_for_goods - logistics - storage - deductions
      seller_profit = total_to_pay - COGS
      margin_pct = seller_profit / revenue * 100
      profitability_pct = seller_profit / COGS * 100
    """
    payout_for_goods = payout_sales - payout_returns
    total_to_pay = payout_for_goods - logistics - storage - deductions
    seller_profit = total_to_pay - cogs
    margin_pct = (seller_profit / revenue * Decimal("100")) if revenue > 0 else None
    profitability_pct = (seller_profit / cogs * Decimal("100")) if cogs > 0 else None
    return SellerKpis(
        revenue=revenue,
        payout_for_goods=payout_for_goods,
        logistics=logistics,
        storage=storage,
        deductions=deductions,
        total_to_pay=total_to_pay,
        cogs=cogs,
        seller_profit=seller_profit,
        margin_pct=margin_pct,
        profitability_pct=profitability_pct,
    )
