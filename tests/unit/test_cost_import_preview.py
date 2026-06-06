"""Cost import preview — Excel date cells must serialize as plain dates."""

from __future__ import annotations

import io
from datetime import date

import pandas as pd

from app.schemas.cost_import import CostImportPreviewResponse
from app.services.cost_service import CostService


def test_preview_import_accepts_excel_datetime_cells() -> None:
    df = pd.DataFrame(
        [
            {
                "Артикул (internal_sku)": "SKU-001",
                "Дата начала (effective_from)": pd.Timestamp("2026-01-01"),
                "Цена закупки (Unit Cost)": 100,
                "Доп. расходы (additional_cost)": 0,
                "Валюта (currency)": "RUB",
            }
        ]
    )
    column_map = CostService._resolve_cost_columns(list(df.columns.astype(str)))
    svc = CostService.__new__(CostService)
    rows = svc._preview_rows(df=df, column_map=column_map, max_rows=20)

    assert len(rows) == 1
    assert rows[0].effective_from == date(2026, 1, 1)

    response = CostImportPreviewResponse(
        detected_columns=column_map,
        total_rows=len(df),
        preview_rows=rows,
        issues=[],
    )
    assert response.preview_rows[0].effective_from == date(2026, 1, 1)


def test_parse_import_date_from_timestamp() -> None:
    assert CostService._parse_import_date(pd.Timestamp("2026-02-15")) == date(2026, 2, 15)


def test_load_cost_import_dataframe_reads_excel() -> None:
    buf = io.BytesIO()
    pd.DataFrame(
        [{"internal_sku": "SKU-1", "effective_from": "2026-01-01", "product_cost": 10}]
    ).to_excel(buf, index=False)
    df = CostService._load_cost_import_dataframe("costs.xlsx", buf.getvalue())
    assert len(df) == 1
    assert "internal_sku" in df.columns


def test_preview_import_via_excel_bytes() -> None:
    df = pd.DataFrame(
        [
            {
                "internal_sku": "SKU-B",
                "effective_from": date(2026, 3, 10),
                "product_cost": 50,
            }
        ]
    )
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    content = buf.getvalue()

    column_map = CostService._resolve_cost_columns(
        list(pd.read_excel(io.BytesIO(content)).columns.astype(str))
    )
    loaded = pd.read_excel(io.BytesIO(content))
    svc = CostService.__new__(CostService)
    rows = svc._preview_rows(df=loaded, column_map=column_map, max_rows=20)

    assert rows[0].internal_sku == "SKU-B"
    assert rows[0].effective_from == date(2026, 3, 10)
