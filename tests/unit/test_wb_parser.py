from datetime import date
from decimal import Decimal

import pandas as pd
from app.domain.finance.ledger import LedgerBuilder
from app.parsers.wb.base import NormalizedWbRow, resolve_column_map
from app.parsers.wb.strategies.realization_v1 import RealizationV1Parser


def test_resolve_column_map_tolerant_ru_headers() -> None:
    columns = ["Дата продажи", "Артикул поставщика", "Комиссия", "К перечислению"]
    resolved = resolve_column_map(columns)
    assert resolved["operation_date"] == "Дата продажи"
    assert resolved["sku"] == "Артикул поставщика"
    assert resolved["commission"] == "Комиссия"
    assert resolved["payout"] == "К перечислению"


def test_realization_v1_parser_normalizes_row() -> None:
    parser = RealizationV1Parser()
    df = pd.DataFrame(
        [
            {
                "Дата продажи": "2026-01-15",
                "Артикул поставщика": "SKU-1",
                "Комиссия": "-120.50",
                "К перечислению": "880.50",
            }
        ]
    )
    rows = parser.parse(df)
    assert len(rows) == 1
    row = rows[0]
    assert row.sku == "SKU-1"
    assert row.operation_date == date(2026, 1, 15)
    assert row.canonical["commission"] == Decimal("-120.50")
    assert row.canonical["payout"] == Decimal("880.50")


def test_ledger_builder_emits_decimal_entries() -> None:
    row = NormalizedWbRow(
        source_row_id="r0",
        source_row_index=0,
        operation_date=date(2026, 1, 15),
        sku="SKU-1",
        nm_id=None,
        canonical={
            "retail_amount": Decimal("1000"),
            "commission": Decimal("100"),
            "payout": Decimal("900"),
        },
        raw={},
    )
    entries = LedgerBuilder.from_normalized_rows([row], default_date=date(2026, 1, 1))
    types = {entry.operation_type.value for entry in entries}
    assert "sale" in types
    assert "commission" in types
    assert all(isinstance(entry.amount, Decimal) for entry in entries)


def test_ledger_builder_does_not_duplicate_returns_when_return_amount_present() -> None:
    row = NormalizedWbRow(
        source_row_id="r1",
        source_row_index=1,
        operation_date=date(2026, 1, 16),
        sku="SKU-1",
        nm_id=None,
        canonical={
            "operation_type": "Возврат товара",
            "retail_amount": Decimal("1000"),
            "return_amount": Decimal("1000"),
        },
        raw={},
    )
    entries = LedgerBuilder.from_normalized_rows([row], default_date=date(2026, 1, 1))
    return_entries = [e for e in entries if e.operation_type.value == "return"]
    assert len(return_entries) == 1
