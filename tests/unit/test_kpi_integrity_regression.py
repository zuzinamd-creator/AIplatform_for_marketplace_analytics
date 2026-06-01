from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.analytics.aggregation import AggregationEngine
from app.domain.finance.types import LedgerEntryDraft
from app.models.finance.enums import LedgerOperationType
from app.models.report import Marketplace


def test_profit_does_not_include_payout_cashflow() -> None:
    """
    Regression guard:
    - PAYOUT is a cash movement and must not inflate net profit.
    - Without this, profit can become larger than revenue (financially impossible).
    """
    day = date(2026, 1, 10)
    entries = [
        LedgerEntryDraft(
            operation_date=day,
            sku="SKU-1",
            nm_id=None,
            operation_type=LedgerOperationType.SALE,
            amount=Decimal("1000"),
            currency="RUB",
            source_row_id="r0:sale",
        ),
        # Typical marketplace cash payout for that sale.
        LedgerEntryDraft(
            operation_date=day,
            sku="SKU-1",
            nm_id=None,
            operation_type=LedgerOperationType.PAYOUT,
            amount=Decimal("900"),
            currency="RUB",
            source_row_id="r0:payout",
        ),
    ]

    daily, _ = AggregationEngine.build(
        entries,
        marketplace=Marketplace.WILDBERRIES,
        costs_by_sku={},
        default_date=day,
    )
    assert len(daily) == 1
    assert daily[0].revenue == Decimal("1000")
    assert daily[0].net_profit == Decimal("1000")

