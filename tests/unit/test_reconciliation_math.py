from decimal import Decimal

from app.domain.economics.reconciliation_math import expected_payout


def test_expected_payout_excludes_cogs_and_matches_components() -> None:
    res = expected_payout(
        revenue=Decimal("1000"),
        returns_amount=Decimal("100"),
        commissions=Decimal("50"),
        logistics=Decimal("20"),
        storage=Decimal("10"),
        ads=Decimal("30"),
        penalties=Decimal("5"),
        acquiring=Decimal("3"),
        deductions=Decimal("2"),
        compensation=Decimal("7"),
    )
    assert res == Decimal("787")

