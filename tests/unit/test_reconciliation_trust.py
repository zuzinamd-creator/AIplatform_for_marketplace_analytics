"""Reconciliation profit trust contract (Phase 9.7-D)."""

from decimal import Decimal

from app.domain.analytics.profit_trust import apply_profit_trust_to_kpis
from app.schemas.analytics import ReconciliationBreakdown


def test_reconciliation_profit_gated_like_revenue_kpi() -> None:
    """Reconciliation profit follows the same backend trust contract as revenue KPIs."""
    raw_profit = Decimal("15000.50")
    for trust, expected in [
        ("full", Decimal("15000.50")),
        ("partial", Decimal("15000.50")),
        ("insufficient", None),
    ]:
        profit_out, _ = apply_profit_trust_to_kpis(
            trust=trust,
            total_profit=raw_profit,
            margin_pct=None,
        )
        assert profit_out == expected


def test_reconciliation_breakdown_accepts_null_profit() -> None:
    breakdown = ReconciliationBreakdown(
        revenue=Decimal("1000"),
        returns_amount=Decimal("0"),
        commissions=Decimal("100"),
        logistics=Decimal("50"),
        storage=Decimal("10"),
        ads=Decimal("20"),
        penalties=Decimal("0"),
        acquiring=Decimal("5"),
        deductions=Decimal("0"),
        compensation=Decimal("0"),
        cogs=Decimal("0"),
        expected_payout=Decimal("815"),
        actual_payout=Decimal("800"),
        payout_difference=Decimal("-15"),
        profit=None,
        payout_is_not_profit_explanation="test",
    )
    assert breakdown.profit is None
