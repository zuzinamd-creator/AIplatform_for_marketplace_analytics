"""Profit KPI trust classification based on SKU cost coverage."""

from __future__ import annotations

from decimal import Decimal

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
