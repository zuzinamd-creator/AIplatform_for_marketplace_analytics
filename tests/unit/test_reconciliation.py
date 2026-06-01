from datetime import date
from decimal import Decimal

from app.domain.finance.types import LedgerEntryDraft
from app.domain.reconciliation.calculator import ReconciliationCalculator
from app.models.finance.enums import LedgerOperationType


def test_reconciliation_is_deterministic() -> None:
    entries = [
        LedgerEntryDraft(
            operation_date=date(2026, 1, 1),
            sku="SKU-1",
            nm_id="123",
            operation_type=LedgerOperationType.SALE,
            amount=Decimal("1000.00"),
            currency="RUB",
            source_row_id="r1:sale",
        ),
        LedgerEntryDraft(
            operation_date=date(2026, 1, 1),
            sku="SKU-1",
            nm_id="123",
            operation_type=LedgerOperationType.COMMISSION,
            amount=Decimal("-100.00"),
            currency="RUB",
            source_row_id="r1:commission",
        ),
        LedgerEntryDraft(
            operation_date=date(2026, 1, 1),
            sku="SKU-1",
            nm_id="123",
            operation_type=LedgerOperationType.PAYOUT,
            amount=Decimal("850.00"),
            currency="RUB",
            source_row_id="r1:payout",
        ),
    ]
    result = ReconciliationCalculator.calculate(entries)
    assert result.gross_revenue == Decimal("1000.00")
    assert result.wb_commissions == Decimal("100.00")
    assert result.expected_payout == Decimal("900.00")
    assert result.actual_payout == Decimal("850.00")
    assert result.difference == Decimal("-50.00")
