"""Variant A profit math + AI/dashboard primary alignment (Phase 9.9-R15)."""

from __future__ import annotations

from decimal import Decimal

from app.domain.analytics.promotion_adjusted import (
    compute_profit_after_promotion,
    compute_promotion_impact_pct,
)
from app.domain.analytics.seller_kpis import compute_seller_kpis
from tests.unit.test_seller_kpi_math import PILOT_EXPECTED

TOLERANCE = Decimal("0.01")

# R13 / R14A confirmed case (FULL week 2026-06-15 → 2026-06-21)
R15_DEDUCTIONS = Decimal("33652.00")
R15_PROMO = Decimal("10662.00")
R15_JAM = Decimal("22990.00")


def _assert_close(actual: Decimal, expected: Decimal, label: str) -> None:
    delta = abs(actual - expected)
    assert delta <= TOLERANCE, f"{label}: expected {expected}, got {actual} (delta {delta})"


def test_variant_a_no_double_count_r15_case() -> None:
    """
    deductions = promo + jam = 33652 must NOT be subtracted again from profit.

    profit = total_to_pay − COGS
    """
    settlement = Decimal("200000.00")
    cogs = Decimal("80000.00")
    revenue = Decimal("400000.00")

    # Settlement already net of deductions (as compute_seller_kpis produces).
    seller = compute_seller_kpis(
        revenue=revenue,
        payout_sales=Decimal("260000.00"),
        payout_returns=Decimal("10000.00"),
        logistics=Decimal("15000.00"),
        storage=Decimal("1348.00"),
        deductions=R15_DEDUCTIONS,
        cogs=cogs,
    )
    _assert_close(seller.deductions, R15_DEDUCTIONS, "deductions")
    _assert_close(seller.total_to_pay, settlement, "total_to_pay")
    expected_profit = settlement - cogs

    adjusted = compute_profit_after_promotion(
        settlement_wb=seller.total_to_pay,
        wb_promotion_expenses=R15_PROMO,
        jam_subscription_expenses=R15_JAM,
        cogs=cogs,
        revenue=revenue,
    )
    _assert_close(adjusted.manual_expenses_total, R15_PROMO + R15_JAM, "manual_total")
    _assert_close(adjusted.manual_expenses_total, R15_DEDUCTIONS, "manual_equals_deductions")
    # No second subtract:
    _assert_close(adjusted.adjusted_settlement, seller.total_to_pay, "adjusted_eq_settlement")
    _assert_close(adjusted.seller_profit_raw, expected_profit, "profit_raw")
    _assert_close(adjusted.seller_profit_after_promotion, expected_profit, "profit_primary")
    _assert_close(adjusted.seller_profit_after_promotion, seller.seller_profit, "alias_matches_seller")
    assert adjusted.seller_profit_after_promotion != expected_profit - R15_DEDUCTIONS


def test_variant_a_pilot_primary_equals_settlement_profit() -> None:
    adjusted = compute_profit_after_promotion(
        settlement_wb=PILOT_EXPECTED["total_to_pay"],
        wb_promotion_expenses=Decimal("9925.00"),
        jam_subscription_expenses=Decimal("0"),
        cogs=PILOT_EXPECTED["cogs"],
        revenue=PILOT_EXPECTED["revenue"],
    )
    _assert_close(adjusted.seller_profit_after_promotion, PILOT_EXPECTED["seller_profit"], "primary")
    _assert_close(adjusted.seller_profit_raw, PILOT_EXPECTED["seller_profit"], "raw")
    _assert_close(adjusted.adjusted_settlement, PILOT_EXPECTED["total_to_pay"], "settlement")
    assert adjusted.margin_pct is not None
    _assert_close(
        adjusted.margin_pct.quantize(Decimal("0.01")),
        PILOT_EXPECTED["margin_pct"],
        "margin",
    )


def test_promotion_impact_omitted_when_no_second_subtract() -> None:
    impact = compute_promotion_impact_pct(
        seller_profit_raw=Decimal("100530.15"),
        seller_profit_after_promotion=Decimal("100530.15"),
    )
    assert impact is None


def test_ai_primary_aligns_with_dashboard_profit_fields() -> None:
    """
    AI metrics_snapshot primary profit fields must equal dashboard gross/total profit
    (= seller.seller_profit), not settlement − promo − jam.
    """
    seller = compute_seller_kpis(
        revenue=Decimal("400000"),
        payout_sales=Decimal("260000"),
        payout_returns=Decimal("10000"),
        logistics=Decimal("15000"),
        storage=Decimal("1348"),
        deductions=R15_DEDUCTIONS,
        cogs=Decimal("80000"),
    )
    adjusted = compute_profit_after_promotion(
        settlement_wb=seller.total_to_pay,
        wb_promotion_expenses=R15_PROMO,
        jam_subscription_expenses=R15_JAM,
        cogs=seller.cogs,
        revenue=seller.revenue,
    )
    # Dashboard: gross_profit / total_profit
    dashboard_primary = seller.seller_profit
    # AI: total_profit / seller_profit / seller_profit_after_promotion
    ai_total_profit = adjusted.seller_profit_after_promotion
    ai_seller_profit = adjusted.seller_profit_raw
    assert dashboard_primary == ai_total_profit == ai_seller_profit
    assert dashboard_primary == seller.total_to_pay - seller.cogs
