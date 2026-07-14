"""Canonical FINANCE report selection for settlement KPIs (Phase 9.9-R15)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID


@dataclass(frozen=True)
class FinanceReportCandidate:
    """Minimal period metadata needed to resolve overlapping FINANCE reports."""

    id: UUID
    period_start: date
    period_end: date
    created_at: datetime | None = None


def inclusive_span_days(period_start: date, period_end: date) -> int:
    """Inclusive day count for [start, end]."""
    return (period_end - period_start).days + 1


def is_proper_subset(inner: FinanceReportCandidate, outer: FinanceReportCandidate) -> bool:
    """True when inner period is strictly nested inside outer (same bounds excluded)."""
    if inner.period_start < outer.period_start or inner.period_end > outer.period_end:
        return False
    return (
        inner.period_start > outer.period_start
        or inner.period_end < outer.period_end
    )


def _created_sort_key(created_at: datetime | None) -> datetime:
    if created_at is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if created_at.tzinfo is None:
        return created_at.replace(tzinfo=timezone.utc)
    return created_at


def select_canonical_finance_reports(
    candidates: list[FinanceReportCandidate],
) -> list[FinanceReportCandidate]:
    """
    Resolve overlapping FINANCE reports for KPI settlement scope.

    Rules:
    1. Prefer longest inclusive period coverage.
    2. Exclude nested/subset reports (e.g. SHORT 15–20 inside FULL 15–21).
    3. For identical periods, keep the latest by created_at.
    4. Keep multiple non-nested reports (adjacent weeks still sum).
    """
    if not candidates:
        return []

    ordered = sorted(
        candidates,
        key=lambda c: (
            inclusive_span_days(c.period_start, c.period_end),
            c.period_end,
            _created_sort_key(c.created_at),
        ),
        reverse=True,
    )

    selected: list[FinanceReportCandidate] = []
    for candidate in ordered:
        if any(
            candidate.period_start == kept.period_start
            and candidate.period_end == kept.period_end
            for kept in selected
        ):
            continue
        if any(is_proper_subset(candidate, kept) for kept in selected):
            continue
        selected.append(candidate)
    return selected


def select_canonical_finance_report_ids(
    candidates: list[FinanceReportCandidate],
) -> list[UUID]:
    return [c.id for c in select_canonical_finance_reports(candidates)]
