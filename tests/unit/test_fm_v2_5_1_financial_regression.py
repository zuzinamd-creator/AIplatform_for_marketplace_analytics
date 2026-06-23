import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.domain.finance.ledger import LedgerBuilder
from app.models.finance.enums import LedgerOperationType
from app.parsers.wb.base import NormalizedWbRow

PILOT_RETURN_ROWS = [
    {"wb": "2633", "retail": "3705", "pvz": "94.335"},
    {"wb": "2562", "retail": "3698", "pvz": "107.604"},
    {"wb": "306", "retail": "470", "pvz": "10.199"},
    {"wb": "292", "retail": "480", "pvz": "8.525"},
    {"wb": "280", "retail": "480", "pvz": "7.82"},
    {"wb": "296", "retail": "470", "pvz": "12.508"},
    {"wb": "305", "retail": "494", "pvz": "7.82"},
    {"wb": "322", "retail": "509", "pvz": "9.028"},
    {"wb": "343", "retail": "543", "pvz": "11.446"},
    {"wb": "324", "retail": "509", "pvz": "9.851"},
    {"wb": "305", "retail": "494", "pvz": "7.82"},
    {"wb": "322", "retail": "509", "pvz": "9.028"},
    {"wb": "354", "retail": "477", "pvz": "0"},
    {"wb": "298", "retail": "460", "pvz": "7.579"},
]
PILOT_RETURN_WB_TOTAL = Decimal("8942.00")


def _return_row(
    *,
    row_id: str,
    index: int,
    return_wb: Decimal | None = None,
    wb_realized_amount: Decimal | None = None,
    retail_amount: Decimal | None = None,
    return_amount: Decimal | None = None,
) -> NormalizedWbRow:
    canonical: dict[str, object] = {"operation_type": "Возврат"}
    if return_wb is not None:
        canonical["return_wb"] = return_wb
    if wb_realized_amount is not None:
        canonical["wb_realized_amount"] = wb_realized_amount
    if retail_amount is not None:
        canonical["retail_amount"] = retail_amount
    if return_amount is not None:
        canonical["return_amount"] = return_amount
    return NormalizedWbRow(
        source_row_id=row_id,
        source_row_index=index,
        operation_date=date(2026, 5, 14),
        sku="SKU-RET",
        nm_id=None,
        canonical=canonical,
        raw={},
    )


def test_return_row_uses_wb_not_qty() -> None:
    row = _return_row(
        row_id="r-wb",
        index=0,
        return_wb=Decimal("2562"),
        retail_amount=Decimal("3698"),
        return_amount=Decimal("107.6"),
    )
    entries = LedgerBuilder.from_normalized_rows([row], default_date=date(2026, 5, 14))
    ret = next(e for e in entries if e.operation_type == LedgerOperationType.RETURN)
    assert ret.amount == Decimal("-2562")
    assert len([e for e in entries if e.operation_type == LedgerOperationType.RETURN]) == 1


def test_return_row_fallback_to_wb_realized() -> None:
    row = _return_row(
        row_id="r-wb-fallback",
        index=1,
        wb_realized_amount=Decimal("2562"),
        retail_amount=Decimal("3698"),
        return_amount=Decimal("107.6"),
    )
    entries = LedgerBuilder.from_normalized_rows([row], default_date=date(2026, 5, 14))
    ret = next(e for e in entries if e.operation_type == LedgerOperationType.RETURN)
    assert ret.amount == Decimal("-2562")
    assert ret.entry_metadata is not None
    assert ret.entry_metadata["return_basis"] == "wb"


def test_return_row_fallback_to_retail_amount() -> None:
    row = _return_row(
        row_id="r-gmv-fallback",
        index=2,
        retail_amount=Decimal("3698"),
        return_amount=Decimal("107.6"),
    )
    entries = LedgerBuilder.from_normalized_rows([row], default_date=date(2026, 5, 14))
    ret = next(e for e in entries if e.operation_type == LedgerOperationType.RETURN)
    assert ret.amount == Decimal("-3698")
    assert ret.entry_metadata is not None
    assert ret.entry_metadata["return_basis"] == "gmv"


def test_return_metadata_contains_return_basis() -> None:
    row = _return_row(
        row_id="r-meta",
        index=3,
        return_wb=Decimal("2562"),
        wb_realized_amount=Decimal("2562"),
    )
    entries = LedgerBuilder.from_normalized_rows([row], default_date=date(2026, 5, 14))
    ret = next(e for e in entries if e.operation_type == LedgerOperationType.RETURN)
    assert ret.entry_metadata is not None
    assert ret.entry_metadata["return_basis"] == "wb"
    assert ret.entry_metadata["wb_realized_amount"] == "2562"
    assert ret.entry_metadata["parser_row_index"] == "3"


def test_sale_metadata_contains_wb_realized() -> None:
    row = NormalizedWbRow(
        source_row_id="r-sale",
        source_row_index=4,
        operation_date=date(2026, 5, 1),
        sku="SKU-1",
        nm_id=None,
        canonical={
            "operation_type": "Продажа",
            "retail_amount": Decimal("509"),
            "wb_realized_amount": Decimal("480"),
            "commission": Decimal("12.36"),
            "payout": Decimal("400"),
            "quantity": 2,
        },
        raw={},
    )
    entries = LedgerBuilder.from_normalized_rows([row], default_date=date(2026, 5, 1))
    sale = next(e for e in entries if e.operation_type == LedgerOperationType.SALE)
    assert sale.amount == Decimal("509")
    assert sale.entry_metadata is not None
    assert sale.entry_metadata["wb_realized_amount"] == "480"
    assert sale.entry_metadata["quantity"] == "2"
    assert "return_basis" not in sale.entry_metadata


def test_pilot_return_invariant() -> None:
    rows = [
        NormalizedWbRow(
            source_row_id=f"pilot-ret-{idx}",
            source_row_index=idx,
            operation_date=date(2026, 5, 1),
            sku=f"sku-{idx}",
            nm_id=None,
            canonical={
                "operation_type": "Возврат",
                "return_wb": Decimal(sample["wb"]),
                "wb_realized_amount": Decimal(sample["wb"]),
                "retail_amount": Decimal(sample["retail"]),
                "return_amount": Decimal(sample["pvz"]),
            },
            raw={},
        )
        for idx, sample in enumerate(PILOT_RETURN_ROWS)
    ]
    entries = LedgerBuilder.from_normalized_rows(rows, default_date=date(2026, 5, 1))
    return_total = sum(
        abs(entry.amount)
        for entry in entries
        if entry.operation_type == LedgerOperationType.RETURN
    )
    assert return_total == PILOT_RETURN_WB_TOTAL


def test_pilot_return_invariant_from_audit_fixture() -> None:
    fixture = Path("tmp_fm_v2_audit_detail.json")
    if not fixture.exists():
        return
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    rows: list[NormalizedWbRow] = []
    for idx, sample in enumerate(payload.get("return_rows", [])):
        if sample.get("op") != "Возврат":
            continue
        rows.append(
            NormalizedWbRow(
                source_row_id=f"audit-ret-{idx}",
                source_row_index=idx,
                operation_date=date(2026, 5, 1),
                sku=str(sample.get("sku", f"sku-{idx}")),
                nm_id=None,
                canonical={
                    "operation_type": "Возврат",
                    "return_wb": Decimal(str(sample["wb"])),
                    "wb_realized_amount": Decimal(str(sample["wb"])),
                    "retail_amount": Decimal(str(sample["retail"])),
                    "return_amount": Decimal(str(sample["pvz"])),
                },
                raw={},
            )
        )
    entries = LedgerBuilder.from_normalized_rows(rows, default_date=date(2026, 5, 1))
    return_total = sum(
        abs(entry.amount)
        for entry in entries
        if entry.operation_type == LedgerOperationType.RETURN
    )
    assert return_total == PILOT_RETURN_WB_TOTAL
