"""Canonical FINANCE report selection (Phase 9.9-R15 overlap fix)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

from app.domain.analytics.canonical_reports import (
    FinanceReportCandidate,
    inclusive_span_days,
    is_proper_subset,
    select_canonical_finance_report_ids,
    select_canonical_finance_reports,
)


def _c(
    *,
    start: date,
    end: date,
    created: datetime | None = None,
) -> FinanceReportCandidate:
    return FinanceReportCandidate(
        id=uuid4(),
        period_start=start,
        period_end=end,
        created_at=created,
    )


def test_full_week_excludes_nested_short() -> None:
    """FULL 15–21 wins over SHORT 15–20 when both overlap a KPI window."""
    full = _c(start=date(2026, 6, 15), end=date(2026, 6, 21))
    short = _c(start=date(2026, 6, 15), end=date(2026, 6, 20))
    selected = select_canonical_finance_reports([short, full])
    assert len(selected) == 1
    assert selected[0].id == full.id
    assert select_canonical_finance_report_ids([short, full]) == [full.id]


def test_adjacent_weeks_both_kept() -> None:
    week_a = _c(start=date(2026, 6, 8), end=date(2026, 6, 14))
    week_b = _c(start=date(2026, 6, 15), end=date(2026, 6, 21))
    selected_ids = set(select_canonical_finance_report_ids([week_a, week_b]))
    assert selected_ids == {week_a.id, week_b.id}


def test_identical_period_keeps_latest_created() -> None:
    older = _c(
        start=date(2026, 6, 15),
        end=date(2026, 6, 21),
        created=datetime(2026, 6, 22, tzinfo=timezone.utc),
    )
    newer = _c(
        start=date(2026, 6, 15),
        end=date(2026, 6, 21),
        created=datetime(2026, 6, 23, tzinfo=timezone.utc),
    )
    selected = select_canonical_finance_reports([older, newer])
    assert len(selected) == 1
    assert selected[0].id == newer.id


def test_proper_subset_helpers() -> None:
    full = _c(start=date(2026, 6, 15), end=date(2026, 6, 21))
    short = _c(start=date(2026, 6, 15), end=date(2026, 6, 20))
    assert inclusive_span_days(full.period_start, full.period_end) == 7
    assert inclusive_span_days(short.period_start, short.period_end) == 6
    assert is_proper_subset(short, full)
    assert not is_proper_subset(full, short)
    assert not is_proper_subset(full, full)
