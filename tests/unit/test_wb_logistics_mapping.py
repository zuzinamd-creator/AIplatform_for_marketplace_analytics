from pathlib import Path

from app.parsers.wb.base import resolve_column_map
from app.parsers.wb.header_detection import locate_wb_table
from app.parsers.wb.rehydrate import canonical_from_raw_payload
from app.parsers.wb.streaming import iter_wb_normalized_rows


def test_wb_detailed_report_maps_logistics_column() -> None:
    fixture = Path("tests/Еженедельный детализированный отчет WB.xlsx")
    located = locate_wb_table(fixture, filename=fixture.name)
    column_map = resolve_column_map(located.headers)
    assert column_map.get("logistics") == "Услуги по доставке товара покупателю"

    for _, chunk in iter_wb_normalized_rows(fixture, filename=fixture.name):
        assert any(row.canonical.get("logistics") not in (None, 0) for row in chunk)
        break


def test_rehydrate_logistics_from_stored_raw() -> None:
    raw = {"Услуги по доставке товара покупателю": "40.46", "Артикул поставщика": "sku-1"}
    canonical = canonical_from_raw_payload(raw)
    assert canonical.get("logistics") is not None
    assert str(canonical["logistics"]) == "40.46"
