"""Seller profit KPI math (Phase 7.8 pilot period fixture)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.analytics.seller_kpis import compute_seller_kpis

PILOT_PERIOD = (date(2026, 6, 29), date(2026, 7, 5))

PILOT_EXPECTED = {
    "revenue": Decimal("501414.11"),
    "payout_for_goods": Decimal("347894.94"),
    "logistics": Decimal("40218.31"),
    "storage": Decimal("3407.85"),
    "deductions": Decimal("9925.00"),
    "total_to_pay": Decimal("294343.78"),
    "cogs": Decimal("193813.63"),
    "seller_profit": Decimal("100530.15"),
    "margin_pct": Decimal("20.05"),
    "profitability_pct": Decimal("51.87"),
}

TOLERANCE = Decimal("0.01")


def _assert_close(actual: Decimal, expected: Decimal, label: str) -> None:
    delta = abs(actual - expected)
    assert delta <= TOLERANCE, f"{label}: expected {expected}, got {actual} (delta {delta})"


def test_compute_seller_kpis_pilot_period_fixture() -> None:
    """Pure math fixture for WB pilot week 29.06–05.07.2026."""
    kpis = compute_seller_kpis(
        revenue=PILOT_EXPECTED["revenue"],
        payout_sales=Decimal("349853.23"),
        payout_returns=Decimal("1958.29"),
        logistics=PILOT_EXPECTED["logistics"],
        storage=PILOT_EXPECTED["storage"],
        deductions=PILOT_EXPECTED["deductions"],
        cogs=PILOT_EXPECTED["cogs"],
    )
    _assert_close(kpis.revenue, PILOT_EXPECTED["revenue"], "revenue")
    _assert_close(kpis.payout_for_goods, PILOT_EXPECTED["payout_for_goods"], "payout_for_goods")
    _assert_close(kpis.logistics, PILOT_EXPECTED["logistics"], "logistics")
    _assert_close(kpis.storage, PILOT_EXPECTED["storage"], "storage")
    _assert_close(kpis.deductions, PILOT_EXPECTED["deductions"], "deductions")
    _assert_close(kpis.total_to_pay, PILOT_EXPECTED["total_to_pay"], "total_to_pay")
    _assert_close(kpis.cogs, PILOT_EXPECTED["cogs"], "cogs")
    _assert_close(kpis.seller_profit, PILOT_EXPECTED["seller_profit"], "seller_profit")
    assert kpis.margin_pct is not None
    _assert_close(kpis.margin_pct.quantize(Decimal("0.01")), PILOT_EXPECTED["margin_pct"], "margin_pct")
    assert kpis.profitability_pct is not None
    _assert_close(
        kpis.profitability_pct.quantize(Decimal("0.01")),
        PILOT_EXPECTED["profitability_pct"],
        "profitability_pct",
    )
