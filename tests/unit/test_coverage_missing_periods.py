from __future__ import annotations

from datetime import date

from app.schemas.analytics import MissingPeriodRange
from app.services.analytics_service import _compute_missing_ranges


def test_compute_missing_ranges_single_gap() -> None:
    days = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 5)]
    missing = _compute_missing_ranges(days)
    assert missing == [
        MissingPeriodRange(start=date(2026, 1, 3), end=date(2026, 1, 4), missing_days=2)
    ]


def test_compute_missing_ranges_no_gaps() -> None:
    days = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]
    assert _compute_missing_ranges(days) == []

