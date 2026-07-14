"""Phase 9.9-R15B — revenue from canonical FINANCE reports (no SHORT overlap)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.domain.analytics.canonical_reports import (
    FinanceReportCandidate,
    select_canonical_finance_report_ids,
)
from app.domain.analytics.seller_kpis import compute_seller_kpis

TOLERANCE = Decimal("0.01")

# Confirmed FULL ledger SALE for 2026-06-15 → 2026-06-21 (excludes SHORT 12_514.57)
FULL_REVENUE = Decimal("513089.00")
SHORT_EXTRA_REVENUE = Decimal("12514.57")
INFLATED_DAILY_AGG_REVENUE = FULL_REVENUE + SHORT_EXTRA_REVENUE  # 525603.57

FULL_PAYOUT = Decimal("356330.92")
FULL_LOGISTICS = Decimal("44927.61")
FULL_STORAGE = Decimal("3207.86")
FULL_DEDUCTIONS = Decimal("33652.00")
FULL_COGS = Decimal("197995.49")


def _assert_close(actual: Decimal, expected: Decimal, label: str) -> None:
    delta = abs(actual - expected)
    assert delta <= TOLERANCE, f"{label}: expected {expected}, got {actual} (delta {delta})"


def test_canonical_selection_excludes_short_for_revenue_window() -> None:
    full_id = uuid4()
    short_id = uuid4()
    full = FinanceReportCandidate(
        id=full_id,
        period_start=date(2026, 6, 15),
        period_end=date(2026, 6, 21),
    )
    short = FinanceReportCandidate(
        id=short_id,
        period_start=date(2026, 6, 15),
        period_end=date(2026, 6, 20),
    )
    ids = select_canonical_finance_report_ids([short, full])
    assert ids == [full_id]
    assert short_id not in ids


def test_revenue_kpi_uses_full_sale_not_inflated_daily_aggregate() -> None:
    """Revenue KPI must equal FULL SALE (513089), not daily_aggregates (525603.57)."""
    seller = compute_seller_kpis(
        revenue=FULL_REVENUE,
        payout_sales=FULL_PAYOUT,
        payout_returns=Decimal("0"),
        logistics=FULL_LOGISTICS,
        storage=FULL_STORAGE,
        deductions=FULL_DEDUCTIONS,
        cogs=FULL_COGS,
    )
    _assert_close(seller.revenue, FULL_REVENUE, "revenue")
    assert seller.revenue != INFLATED_DAILY_AGG_REVENUE
    assert INFLATED_DAILY_AGG_REVENUE == Decimal("525603.57")


def test_revenue_payout_settlement_profit_same_canonical_base() -> None:
    """All money KPIs derived from one canonical ledger/settlement path."""
    seller = compute_seller_kpis(
        revenue=FULL_REVENUE,
        payout_sales=FULL_PAYOUT,
        payout_returns=Decimal("0"),
        logistics=FULL_LOGISTICS,
        storage=FULL_STORAGE,
        deductions=FULL_DEDUCTIONS,
        cogs=FULL_COGS,
    )
    expected_settlement = FULL_PAYOUT - FULL_LOGISTICS - FULL_STORAGE - FULL_DEDUCTIONS
    expected_profit = expected_settlement - FULL_COGS
    _assert_close(seller.payout_for_goods, FULL_PAYOUT, "payout")
    _assert_close(seller.total_to_pay, expected_settlement, "settlement")
    _assert_close(seller.seller_profit, expected_profit, "profit")
    _assert_close(seller.revenue, FULL_REVENUE, "revenue_same_set")


def test_margin_and_profitability_use_canonical_revenue_base() -> None:
    seller = compute_seller_kpis(
        revenue=FULL_REVENUE,
        payout_sales=FULL_PAYOUT,
        payout_returns=Decimal("0"),
        logistics=FULL_LOGISTICS,
        storage=FULL_STORAGE,
        deductions=FULL_DEDUCTIONS,
        cogs=FULL_COGS,
    )
    assert seller.margin_pct is not None
    assert seller.profitability_pct is not None
    expected_margin = seller.seller_profit / FULL_REVENUE * Decimal("100")
    expected_profitability = seller.seller_profit / FULL_COGS * Decimal("100")
    _assert_close(seller.margin_pct, expected_margin, "margin_on_full_revenue")
    _assert_close(seller.profitability_pct, expected_profitability, "profitability")
    # Inflated revenue would understate margin:
    inflated_margin = seller.seller_profit / INFLATED_DAILY_AGG_REVENUE * Decimal("100")
    assert seller.margin_pct > inflated_margin
