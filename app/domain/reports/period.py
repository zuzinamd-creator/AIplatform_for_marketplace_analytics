"""Report period bounds derived from WB sale rows."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from app.domain.reports.sale_date import extract_sale_date
from app.models.inventory.enums import InventoryOperationType
from app.parsers.wb.base import NormalizedWbRow
from app.parsers.wb.operation_semantics import resolve_inventory_operation_type

if TYPE_CHECKING:
    pass


def is_wb_sale_payment_justification(operation_label: object) -> bool:
    """True when «Обоснование для оплаты» is a sale (e.g. «Продажа»)."""
    return resolve_inventory_operation_type(operation_label) == InventoryOperationType.SALE


def merge_report_period_bounds(
    bounds: dict[UUID, tuple[date | None, date | None]],
    *,
    report_id: UUID,
    sale_date: date,
) -> None:
    """Extend period bounds with a sale row's «Дата продажи»."""
    existing = bounds.get(report_id)
    if existing is None:
        bounds[report_id] = (sale_date, sale_date)
        return
    period_start, period_end = existing
    if period_start is None or period_end is None:
        bounds[report_id] = (sale_date, sale_date)
        return
    bounds[report_id] = (min(period_start, sale_date), max(period_end, sale_date))


def build_period_bounds_from_row_samples(
    rows: Iterable[tuple[UUID, date, object]],
) -> dict[UUID, tuple[date | None, date | None]]:
    bounds: dict[UUID, tuple[date | None, date | None]] = {}
    for report_id, sale_date, operation_label in rows:
        if not is_wb_sale_payment_justification(operation_label):
            continue
        merge_report_period_bounds(bounds, report_id=report_id, sale_date=sale_date)
    return bounds


def period_bounds_for_wb_rows(
    normalized_rows: Iterable[NormalizedWbRow],
) -> tuple[date | None, date | None]:
    """Sale period for one in-memory WB parse result."""
    sale_dates: list[date] = []
    for row in normalized_rows:
        if not is_wb_sale_payment_justification(row.canonical.get("operation_type")):
            continue
        sale_date = extract_sale_date(canonical=row.canonical, raw_payload=row.raw)
        if sale_date is not None:
            sale_dates.append(sale_date)
    if not sale_dates:
        return None, None
    return min(sale_dates), max(sale_dates)


def attach_period_to_raw_data(
    raw_data: dict | None,
    *,
    period_start: date | None,
    period_end: date | None,
) -> dict:
    """Persist computed sale period alongside the raw snapshot."""
    payload = dict(raw_data or {})
    if period_start is not None:
        payload["period_start"] = period_start.isoformat()
    else:
        payload.pop("period_start", None)
    if period_end is not None:
        payload["period_end"] = period_end.isoformat()
    else:
        payload.pop("period_end", None)
    return payload
