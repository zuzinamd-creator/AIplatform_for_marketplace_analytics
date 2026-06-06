"""Report period bounds derived from WB sale rows."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from app.models.inventory.enums import InventoryOperationType
from app.parsers.wb.operation_semantics import resolve_inventory_operation_type

if TYPE_CHECKING:
    from app.parsers.wb.base import NormalizedWbRow


def is_wb_sale_payment_justification(operation_label: object) -> bool:
    """True when «Обоснование для оплаты» is a sale (e.g. «Продажа»)."""
    return resolve_inventory_operation_type(operation_label) == InventoryOperationType.SALE


def merge_report_period_bounds(
    bounds: dict[UUID, tuple[date | None, date | None]],
    *,
    report_id: UUID,
    operation_date: date,
    operation_label: object,
) -> None:
    """Extend period bounds with a normalized row when it is a sale with a sale date."""
    if not is_wb_sale_payment_justification(operation_label):
        return
    existing = bounds.get(report_id)
    if existing is None:
        bounds[report_id] = (operation_date, operation_date)
        return
    period_start, period_end = existing
    if period_start is None or period_end is None:
        bounds[report_id] = (operation_date, operation_date)
        return
    bounds[report_id] = (min(period_start, operation_date), max(period_end, operation_date))


def build_period_bounds_from_row_samples(
    rows: Iterable[tuple[UUID, date, object]],
) -> dict[UUID, tuple[date | None, date | None]]:
    bounds: dict[UUID, tuple[date | None, date | None]] = {}
    for report_id, operation_date, operation_label in rows:
        merge_report_period_bounds(
            bounds,
            report_id=report_id,
            operation_date=operation_date,
            operation_label=operation_label,
        )
    return bounds


def period_bounds_for_wb_rows(
    normalized_rows: Iterable[NormalizedWbRow],
) -> tuple[date | None, date | None]:
    """Sale period for one in-memory WB parse result."""
    sale_dates: list[date] = []
    for row in normalized_rows:
        if row.operation_date is None:
            continue
        if not is_wb_sale_payment_justification(row.canonical.get("operation_type")):
            continue
        sale_dates.append(row.operation_date)
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
