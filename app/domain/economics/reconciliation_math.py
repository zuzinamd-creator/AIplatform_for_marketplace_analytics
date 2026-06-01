from __future__ import annotations

from decimal import Decimal


def expected_payout(
    *,
    revenue: Decimal,
    returns_amount: Decimal,
    commissions: Decimal,
    logistics: Decimal,
    storage: Decimal,
    ads: Decimal,
    penalties: Decimal,
    acquiring: Decimal,
    deductions: Decimal,
    compensation: Decimal,
) -> Decimal:
    """
    Deterministic expected payout (cash settlement) from components.

    IMPORTANT: payout is cashflow, not profit; COGS is excluded.
    """
    return (
        (revenue - returns_amount)
        - commissions
        - logistics
        - storage
        - ads
        - penalties
        - acquiring
        - deductions
        + compensation
    )

