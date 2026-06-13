"""Unit tests for causal period comparison."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.ai.deep.period_causes import PeriodSnapshot, _append_revenue_causes


def test_revenue_cause_volume_dominant():
    bullets: list[str] = []
    snap_a = PeriodSnapshot(
        revenue=Decimal("474526"),
        profit=Decimal("194549"),
        units=730,
        margin_pct=Decimal("41.0"),
    )
    snap_b = PeriodSnapshot(
        revenue=Decimal("505245"),
        profit=Decimal("229830"),
        units=827,
        margin_pct=Decimal("45.5"),
    )
    rev_pct = Decimal("-6.1")
    line = _append_revenue_causes(bullets, snap_a, snap_b, rev_pct)
    assert bullets
    assert "объём" in bullets[0].lower() or "шт" in bullets[0]
    assert line is not None


def test_revenue_cause_mentions_check_offset():
    bullets: list[str] = []
    snap_a = PeriodSnapshot(Decimal("474526"), Decimal("194549"), 730, Decimal("41"))
    snap_b = PeriodSnapshot(Decimal("505245"), Decimal("229830"), 827, Decimal("45.5"))
    _append_revenue_causes(bullets, snap_a, snap_b, Decimal("-6.1"))
    joined = " ".join(bullets).lower()
    assert "средний чек" in joined
