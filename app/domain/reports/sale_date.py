"""Sale date extraction for report period bounds (Дата продажи)."""

from __future__ import annotations

from datetime import date

from app.parsers.wb.base import normalize_header, parse_date


def extract_sale_date(
    *,
    canonical: dict | None,
    raw_payload: dict | None,
) -> date | None:
    """
    Return «Дата продажи» for a normalized row.

    Period bounds must not use operation_date / order dates — only explicit sale date.
    """
    payload = canonical or {}
    sale = payload.get("sale_date")
    if isinstance(sale, date):
        return sale
    if isinstance(sale, str) and sale.strip():
        parsed = parse_date(sale)
        if parsed is not None:
            return parsed

    for key, value in (raw_payload or {}).items():
        if normalize_header(key) == "дата продажи":
            parsed = parse_date(value)
            if parsed is not None:
                return parsed
    return None
