"""Report period bounds from WB sale rows (Дата продажи + Обоснование для оплаты)."""

from datetime import date
from uuid import uuid4

from app.domain.reports.period import (
    attach_period_to_raw_data,
    is_wb_sale_payment_justification,
    merge_report_period_bounds,
    period_bounds_for_wb_rows,
)
from app.domain.reports.sale_date import extract_sale_date


def test_is_wb_sale_payment_justification_accepts_sale_labels() -> None:
    assert is_wb_sale_payment_justification("Продажа")
    assert is_wb_sale_payment_justification("  Продажа  ")
    assert is_wb_sale_payment_justification("продажа товара")


def test_is_wb_sale_payment_justification_rejects_non_sale_labels() -> None:
    assert not is_wb_sale_payment_justification("Возврат")
    assert not is_wb_sale_payment_justification("Логистика")
    assert not is_wb_sale_payment_justification("")
    assert not is_wb_sale_payment_justification(None)


def test_merge_report_period_bounds_uses_sale_dates() -> None:
    report_id = uuid4()
    bounds: dict = {}
    merge_report_period_bounds(bounds, report_id=report_id, sale_date=date(2026, 1, 10))
    merge_report_period_bounds(bounds, report_id=report_id, sale_date=date(2026, 1, 20))
    assert bounds[report_id] == (date(2026, 1, 10), date(2026, 1, 20))


def test_extract_sale_date_prefers_raw_sale_column() -> None:
    sale = extract_sale_date(
        canonical={"operation_date": date(2026, 4, 26), "operation_type": "Продажа"},
        raw_payload={"Дата заказа покупателем": "2026-04-26", "Дата продажи": "2026-05-18"},
    )
    assert sale == date(2026, 5, 18)


def test_period_bounds_for_wb_rows_uses_sale_date_not_order_date() -> None:
    from app.parsers.wb.base import NormalizedWbRow

    rows = [
        NormalizedWbRow(
            source_row_id="row-0",
            source_row_index=0,
            operation_date=date(2026, 4, 26),
            sku="SKU-A",
            nm_id=None,
            canonical={"operation_type": "Продажа", "operation_date": date(2026, 4, 26)},
            raw={"Дата продажи": "2026-05-18"},
        ),
        NormalizedWbRow(
            source_row_id="row-1",
            source_row_index=1,
            operation_date=date(2026, 4, 26),
            sku="SKU-A",
            nm_id=None,
            canonical={"operation_type": "Продажа", "operation_date": date(2026, 4, 26)},
            raw={"Дата продажи": "2026-05-24"},
        ),
        NormalizedWbRow(
            source_row_id="row-2",
            source_row_index=2,
            operation_date=date(2026, 1, 5),
            sku="SKU-A",
            nm_id=None,
            canonical={"operation_type": "Возврат"},
            raw={"Дата продажи": "2026-01-05"},
        ),
    ]
    assert period_bounds_for_wb_rows(rows) == (date(2026, 5, 18), date(2026, 5, 24))


def test_attach_period_to_raw_data() -> None:
    payload = attach_period_to_raw_data(
        {"columns": [], "row_count": 1},
        period_start=date(2026, 1, 10),
        period_end=date(2026, 1, 20),
    )
    assert payload["period_start"] == "2026-01-10"
    assert payload["period_end"] == "2026-01-20"
    assert payload["row_count"] == 1
