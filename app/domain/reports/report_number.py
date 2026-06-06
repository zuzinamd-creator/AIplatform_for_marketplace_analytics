"""Extract WB/Ozon report numbers from upload filenames."""

from __future__ import annotations

import re

from app.models.report import Marketplace

_WB_REPORT_NUMBER = re.compile(r"№\s*(\d+)", re.IGNORECASE)
_OZON_REPORT_NUMBER = re.compile(r"(?:report[_-]?|^)(\d{6,})", re.IGNORECASE)


def extract_report_number(*, filename: str, marketplace: Marketplace | str) -> str | None:
    """Return marketplace report number when present in the original filename."""
    if not filename.strip():
        return None
    wb_match = _WB_REPORT_NUMBER.search(filename)
    if wb_match:
        return wb_match.group(1)
    mp = marketplace.value if hasattr(marketplace, "value") else str(marketplace).lower()
    if mp == Marketplace.OZON.value or mp == "ozon":
        ozon_match = _OZON_REPORT_NUMBER.search(filename)
        if ozon_match:
            return ozon_match.group(1)
    return None
