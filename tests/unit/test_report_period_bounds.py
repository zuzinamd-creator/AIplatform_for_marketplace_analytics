"""Report period bounds from WB sale rows (Дата продажи + Обоснование для оплаты)."""

from datetime import date
from uuid import uuid4

from app.domain.reports.period import is_wb_sale_payment_justification, merge_report_period_bounds, period_bounds_for_wb_rows, attach_period_to_raw_data


def test_is_wb_sale_payment_justification_accepts_sale_labels() -> None:
    assert is_wb_sale_payment_justification("Продажа")
    assert is_wb_sale_payment_justification("  Продажа  ")
    assert is_wb_sale_payment_justification("продажа товара")


def test_is_wb_sale_payment_justification_rejects_non_sale_labels() -> None:
    assert not is_wb_sale_payment_justification("Возврат")
    assert not is_wb_sale_payment_justification("Логистика")
    assert not is_wb_sale_payment_justification("")
    assert not is_wb_sale_payment_justification(None)


def test_merge_report_period_bounds_uses_only_sale_rows() -> None:
    report_id = uuid4()
    bounds: dict = {}
    merge_report_period_bounds(
        bounds,
        report_id=report_id,
        operation_date=date(2026, 1, 10),
        operation_label="Продажа",
    )
    merge_report_period_bounds(
        bounds,
        report_id=report_id,
        operation_date=date(2026, 1, 20),
        operation_label="Продажа",
    )
    merge_report_period_bounds(
        bounds,
        report_id=report_id,
        operation_date=date(2026, 1, 5),
        operation_label="Возврат",
    )
    assert bounds[report_id] == (date(2026, 1, 10), date(2026, 1, 20))


def test_period_bounds_for_wb_rows() -> None:
    from app.parsers.wb.base import NormalizedWbRow

    rows = [
        NormalizedWbRow(
            source_row_id="row-0",
            source_row_index=0,
            operation_date=date(2026, 1, 10),
            sku="SKU-A",
            nm_id=None,
            canonical={"operation_type": "Продажа"},
            raw={},
        ),
        NormalizedWbRow(
            source_row_id="row-1",
            source_row_index=1,
            operation_date=date(2026, 1, 20),
            sku="SKU-A",
            nm_id=None,
            canonical={"operation_type": "Продажа"},
            raw={},
        ),
        NormalizedWbRow(
            source_row_id="row-2",
            source_row_index=2,
            operation_date=date(2026, 1, 5),
            sku="SKU-A",
            nm_id=None,
            canonical={"operation_type": "Возврат"},
            raw={},
        ),
    ]
    assert period_bounds_for_wb_rows(rows) == (date(2026, 1, 10), date(2026, 1, 20))


def test_attach_period_to_raw_data() -> None:
    payload = attach_period_to_raw_data(
        {"columns": [], "row_count": 1},
        period_start=date(2026, 1, 10),
        period_end=date(2026, 1, 20),
    )
    assert payload["period_start"] == "2026-01-10"
    assert payload["period_end"] == "2026-01-20"
    assert payload["row_count"] == 1
