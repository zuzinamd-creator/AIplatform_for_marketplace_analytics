"""Manual expense annotation math (Phase 9.9-R15 Variant A — no second subtract)."""

from __future__ import annotations

from decimal import Decimal

from app.domain.analytics.promotion_adjusted import (
    compute_profit_after_promotion,
    compute_promotion_impact_pct,
)
from tests.unit.test_seller_kpi_math import PILOT_EXPECTED

TOLERANCE = Decimal("0.01")
WB_PROMOTION = Decimal("9925.00")
JAM_SUBSCRIPTION = Decimal("500.00")


def _assert_close(actual: Decimal, expected: Decimal, label: str) -> None:
    delta = abs(actual - expected)
    assert delta <= TOLERANCE, f"{label}: expected {expected}, got {actual} (delta {delta})"


def test_compute_profit_after_promotion_variant_a_no_second_subtract() -> None:
    adjusted = compute_profit_after_promotion(
        settlement_wb=PILOT_EXPECTED["total_to_pay"],
        wb_promotion_expenses=WB_PROMOTION,
        cogs=PILOT_EXPECTED["cogs"],
        revenue=PILOT_EXPECTED["revenue"],
    )
    _assert_close(adjusted.settlement_wb, PILOT_EXPECTED["total_to_pay"], "settlement_wb")
    _assert_close(adjusted.wb_promotion_expenses, WB_PROMOTION, "wb_promotion_expenses")
    _assert_close(adjusted.jam_subscription_expenses, Decimal("0"), "jam_subscription_expenses")
    _assert_close(adjusted.manual_expenses_total, WB_PROMOTION, "manual_expenses_total")
    # Variant A: adjusted_settlement is NOT reduced by manual expenses.
    _assert_close(
        adjusted.adjusted_settlement,
        PILOT_EXPECTED["total_to_pay"],
        "adjusted_settlement",
    )
    _assert_close(adjusted.seller_profit_raw, PILOT_EXPECTED["seller_profit"], "seller_profit_raw")
    _assert_close(
        adjusted.seller_profit_after_promotion,
        PILOT_EXPECTED["seller_profit"],
        "profit_primary",
    )
    assert adjusted.margin_pct is not None
    _assert_close(adjusted.margin_pct.quantize(Decimal("0.01")), PILOT_EXPECTED["margin_pct"], "margin")
    assert adjusted.profitability_pct is not None
    _assert_close(
        adjusted.profitability_pct.quantize(Decimal("0.01")),
        PILOT_EXPECTED["profitability_pct"],
        "profitability",
    )


def test_zero_promotion_keeps_profit() -> None:
    adjusted = compute_profit_after_promotion(
        settlement_wb=PILOT_EXPECTED["total_to_pay"],
        wb_promotion_expenses=Decimal("0"),
        jam_subscription_expenses=Decimal("0"),
        cogs=PILOT_EXPECTED["cogs"],
        revenue=PILOT_EXPECTED["revenue"],
    )
    _assert_close(adjusted.seller_profit_after_promotion, PILOT_EXPECTED["seller_profit"], "profit")


def test_wb_and_jam_manual_expenses_sum_without_subtract() -> None:
    adjusted = compute_profit_after_promotion(
        settlement_wb=PILOT_EXPECTED["total_to_pay"],
        wb_promotion_expenses=WB_PROMOTION,
        jam_subscription_expenses=JAM_SUBSCRIPTION,
        cogs=PILOT_EXPECTED["cogs"],
        revenue=PILOT_EXPECTED["revenue"],
    )
    total_manual = WB_PROMOTION + JAM_SUBSCRIPTION
    _assert_close(adjusted.manual_expenses_total, total_manual, "manual_expenses_total")
    _assert_close(
        adjusted.seller_profit_after_promotion,
        PILOT_EXPECTED["seller_profit"],
        "profit_not_reduced",
    )


def test_promotion_impact_pct_none_when_equal() -> None:
    impact = compute_promotion_impact_pct(
        seller_profit_raw=PILOT_EXPECTED["seller_profit"],
        seller_profit_after_promotion=PILOT_EXPECTED["seller_profit"],
    )
    assert impact is None
