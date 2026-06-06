"""Re-parse canonical fields from stored WB raw row payloads (mapping fixes)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd

from app.parsers.wb.mapping import CANONICAL_FIELDS
from app.parsers.wb.base import (
    NormalizedWbRow,
    parse_date,
    parse_decimal,
    resolve_column_map,
)


def canonical_from_raw_payload(raw: dict[str, str]) -> dict[str, object]:
    """Rebuild canonical dict using current column alias registry."""
    column_map = resolve_column_map(list(raw.keys()))
    canonical: dict[str, object] = {}
    for field, column in column_map.items():
        if column is None:
            canonical[field] = None
            continue
        value = raw.get(column, "")
        if field == "operation_date":
            canonical[field] = parse_date(value)
        elif field == "sale_date":
            canonical[field] = parse_date(value)
        elif field == "quantity":
            dec = parse_decimal(value)
            canonical[field] = int(dec) if dec is not None else None
        elif field in {"sku", "nm_id", "warehouse_name", "operation_type"}:
            text = str(value).strip() if value is not None and str(value).strip() else None
            canonical[field] = text
        elif field in CANONICAL_FIELDS:
            canonical[field] = parse_decimal(value)
        else:
            canonical[field] = None if value is None or str(value).strip() == "" else str(value).strip()
    return canonical


def normalized_row_from_stored(
    *,
    source_row_id: str,
    source_row_index: int,
    operation_date: date | None,
    sku: str | None,
    nm_id: str | None,
    raw_payload: dict,
    canonical_payload: dict | None = None,
) -> NormalizedWbRow:
    raw = {str(k): "" if v is None else str(v) for k, v in raw_payload.items()}
    canonical = canonical_from_raw_payload(raw)
    op_date = canonical.get("operation_date")
    if isinstance(op_date, date):
        operation_date = op_date
    sku_val = canonical.get("sku")
    nm_val = canonical.get("nm_id")
    return NormalizedWbRow(
        source_row_id=source_row_id,
        source_row_index=source_row_index,
        operation_date=operation_date,
        sku=str(sku_val).strip() if sku_val else sku,
        nm_id=str(nm_val).strip() if nm_val else nm_id,
        canonical=canonical,
        raw=raw,
    )
