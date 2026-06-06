"""Profit KPI trust classification based on SKU cost coverage."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.dto.analytics_dto import TopSKUSummaryDTO

FULL_COVERAGE_THRESHOLD = Decimal("100")
PARTIAL_COVERAGE_THRESHOLD = Decimal("80")
MIN_COVERAGE_THRESHOLD = Decimal("1")


def classify_profit_trust(coverage_pct: Decimal | None) -> str:
    """
    Return trust level for profit/margin KPIs.

    - full: coverage == 100% — profit, margin, ROI are governed
    - partial: 1%..99% — revenue/fees OK; profit/margin may be skewed
    - insufficient: 0% or unknown — profit/margin/ROI must not be shown as factual
    """
    if coverage_pct is None:
        return "insufficient"
    if coverage_pct >= FULL_COVERAGE_THRESHOLD:
        return "full"
    if coverage_pct >= PARTIAL_COVERAGE_THRESHOLD:
        return "partial"
    if coverage_pct >= MIN_COVERAGE_THRESHOLD:
        return "partial"
    return "insufficient"


def apply_profit_trust_to_kpis(
    *,
    trust: str,
    total_profit: Decimal,
    margin_pct: Decimal | None,
) -> tuple[Decimal | None, Decimal | None]:
    """Suppress unreliable profit KPIs for seller-facing responses."""
    if trust == "full":
        return total_profit, margin_pct
    if trust == "partial":
        return total_profit, None
    return None, None


def apply_profit_trust_to_ai_metrics(
    *,
    trust: str,
    total_profit: Decimal | None,
    margin_pct: Decimal | None,
    top_skus: list[TopSKUSummaryDTO],
) -> tuple[Decimal | None, Decimal | None, list[TopSKUSummaryDTO]]:
    """
    Gate all profit-bearing AI metrics consistently with dashboard trust rules.

    When trust != full, SKU-level profit must not leak into LLM prompts.
    """
    from app.dto.analytics_dto import TopSKUSummaryDTO

    if total_profit is None:
        profit_out: Decimal | None = None
    else:
        profit_out, margin_out = apply_profit_trust_to_kpis(
            trust=trust,
            total_profit=total_profit,
            margin_pct=margin_pct,
        )
        margin_pct = margin_out

    if trust == "full":
        return profit_out, margin_pct, top_skus

    gated_top_skus = [
        TopSKUSummaryDTO(
            internal_sku=item.internal_sku,
            revenue=item.revenue,
            profit=Decimal("0"),
            units_sold=item.units_sold,
        )
        for item in top_skus
    ]
    return profit_out, margin_pct, gated_top_skus


def gate_profit_decimal(
    value: Decimal | None,
    *,
    trust: str,
    zero_is_valid: bool = False,
) -> Decimal | None:
    """Hide profit-derived decimals when cost coverage is insufficient."""
    if value is None:
        return None
    if trust == "full":
        return value
    if trust == "partial":
        return value
    return None


def gate_margin_decimal(margin_pct: Decimal | None, *, trust: str) -> Decimal | None:
    if trust == "full":
        return margin_pct
    return None
