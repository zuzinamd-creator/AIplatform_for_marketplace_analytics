from datetime import date
from decimal import Decimal

from app.domain.finance.ledger import LedgerBuilder
from app.domain.finance.wb_row_semantics import classify_wb_finance_row
from app.models.finance.enums import LedgerOperationType
from app.parsers.wb.base import NormalizedWbRow


def test_classify_sale_and_logistics_rows() -> None:
    assert classify_wb_finance_row("Продажа").value == "sale"
    assert classify_wb_finance_row("Логистика").value == "logistics"
    assert classify_wb_finance_row("Возмещение издержек по перевозке/по складским операциям с товаром").value == "reimbursement"


def test_sale_row_does_not_emit_return_from_pvz_column() -> None:
    row = NormalizedWbRow(
        source_row_id="r-sale",
        source_row_index=0,
        operation_date=date(2026, 5, 1),
        sku="SKU-1",
        nm_id=None,
        canonical={
            "operation_type": "Продажа",
            "retail_amount": Decimal("509"),
            "commission": Decimal("12.36"),
            "payout": Decimal("400"),
            "return_amount": Decimal("8.3145"),
            "quantity": 1,
        },
        raw={},
    )
    entries = LedgerBuilder.from_normalized_rows([row], default_date=date(2026, 5, 1))
    types = {entry.operation_type for entry in entries}
    assert LedgerOperationType.SALE in types
    assert LedgerOperationType.COMMISSION in types
    assert LedgerOperationType.RETURN not in types


def test_logistics_row_reads_amount_from_raw_when_canonical_empty() -> None:
    row = NormalizedWbRow(
        source_row_id="r-log",
        source_row_index=1,
        operation_date=date(2026, 5, 2),
        sku="SKU-1",
        nm_id=None,
        canonical={
            "operation_type": "Логистика",
            "logistics": None,
        },
        raw={"Услуги по доставке товара покупателю": "42.76"},
    )
    entries = LedgerBuilder.from_normalized_rows([row], default_date=date(2026, 5, 2))
    logistics = [e for e in entries if e.operation_type == LedgerOperationType.LOGISTICS]
    assert len(logistics) == 1
    assert logistics[0].amount == Decimal("-42.76")
    assert not any(e.operation_type == LedgerOperationType.COMMISSION for e in entries)


def test_return_row_does_not_emit_sale_revenue() -> None:
    row = NormalizedWbRow(
        source_row_id="r-ret",
        source_row_index=3,
        operation_date=date(2026, 5, 4),
        sku="SKU-3",
        nm_id=None,
        canonical={
            "operation_type": "Возврат",
            "retail_amount": Decimal("3698"),
            "commission": Decimal("125.03"),
            "payout": Decimal("-2000"),
        },
        raw={},
    )
    entries = LedgerBuilder.from_normalized_rows([row], default_date=date(2026, 5, 4))
    types = {entry.operation_type for entry in entries}
    assert LedgerOperationType.SALE not in types
    assert LedgerOperationType.RETURN in types
    ret = next(e for e in entries if e.operation_type == LedgerOperationType.RETURN)
    assert ret.amount == Decimal("-3698")


def test_sale_row_stores_quantity_in_metadata() -> None:
    row = NormalizedWbRow(
        source_row_id="r-qty",
        source_row_index=2,
        operation_date=date(2026, 5, 3),
        sku="SKU-2",
        nm_id=None,
        canonical={
            "operation_type": "Продажа",
            "retail_amount": Decimal("1000"),
            "commission": Decimal("100"),
            "payout": Decimal("900"),
            "quantity": 3,
        },
        raw={},
    )
    entries = LedgerBuilder.from_normalized_rows([row], default_date=date(2026, 5, 3))
    sale = next(e for e in entries if e.operation_type == LedgerOperationType.SALE)
    assert sale.entry_metadata is not None
    assert sale.entry_metadata["quantity"] == "3"
