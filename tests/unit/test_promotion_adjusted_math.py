"""Promotion-adjusted profit math (Phase 8.1)."""

from __future__ import annotations

from decimal import Decimal

from app.domain.analytics.promotion_adjusted import compute_profit_after_promotion
from tests.unit.test_seller_kpi_math import PILOT_EXPECTED

TOLERANCE = Decimal("0.01")
PROMOTION = Decimal("9925.00")


def _assert_close(actual: Decimal, expected: Decimal, label: str) -> None:
    delta = abs(actual - expected)
    assert delta <= TOLERANCE, f"{label}: expected {expected}, got {actual} (delta {delta})"


def test_compute_profit_after_promotion_pilot() -> None:
    adjusted = compute_profit_after_promotion(
        settlement_wb=PILOT_EXPECTED["total_to_pay"],
        promotion_expenses=PROMOTION,
        cogs=PILOT_EXPECTED["cogs"],
        revenue=PILOT_EXPECTED["revenue"],
    )
    _assert_close(adjusted.settlement_wb, PILOT_EXPECTED["total_to_pay"], "settlement_wb")
    _assert_close(adjusted.promotion_expenses, PROMOTION, "promotion_expenses")
    _assert_close(
        adjusted.adjusted_settlement,
        PILOT_EXPECTED["total_to_pay"] - PROMOTION,
        "adjusted_settlement",
    )
    _assert_close(adjusted.seller_profit_raw, PILOT_EXPECTED["seller_profit"], "seller_profit_raw")
    _assert_close(adjusted.seller_profit_after_promotion, Decimal("90605.15"), "profit_after")
    assert adjusted.margin_pct is not None
    _assert_close(adjusted.margin_pct.quantize(Decimal("0.01")), Decimal("18.07"), "margin_after")
    assert adjusted.profitability_pct is not None
    _assert_close(
        adjusted.profitability_pct.quantize(Decimal("0.01")),
        Decimal("46.75"),
        "profitability_after",
    )
    assert adjusted.margin_pct_raw is not None
    _assert_close(
        adjusted.margin_pct_raw.quantize(Decimal("0.01")),
        PILOT_EXPECTED["margin_pct"],
        "margin_raw",
    )


def test_zero_promotion_keeps_profit() -> None:
    adjusted = compute_profit_after_promotion(
        settlement_wb=PILOT_EXPECTED["total_to_pay"],
        promotion_expenses=Decimal("0"),
        cogs=PILOT_EXPECTED["cogs"],
        revenue=PILOT_EXPECTED["revenue"],
    )
    _assert_close(adjusted.seller_profit_after_promotion, PILOT_EXPECTED["seller_profit"], "profit")


def test_promotion_impact_pct_pilot() -> None:
    from app.domain.analytics.promotion_adjusted import compute_promotion_impact_pct

    impact = compute_promotion_impact_pct(
        seller_profit_raw=PILOT_EXPECTED["seller_profit"],
        seller_profit_after_promotion=Decimal("90605.15"),
    )
    assert impact is not None
    _assert_close(impact.quantize(Decimal("0.01")), Decimal("9.87"), "promotion_impact_pct")
