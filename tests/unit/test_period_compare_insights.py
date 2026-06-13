"""Tests for period comparison in deep insights."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.ai.deep.period_insights import _append_period_comparison
from app.models.report import Marketplace


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def one(self):
        return self._rows[0]

    def first(self):
        return self._rows[0] if self._rows else None

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


class _FakeDb:
    def __init__(self, responses):
        self._responses = list(responses)

    async def execute(self, _stmt):
        return _FakeResult([self._responses.pop(0)])


@pytest.mark.asyncio
async def test_compare_empty_external_period_uses_split_fallback(monkeypatch):
    bullets: list[str] = []
    extras: dict = {}
    db = _FakeDb(
        [
            (Decimal("100000"), Decimal("40000")),  # primary totals
            (Decimal("0"), Decimal("0")),  # compare totals empty
            date(2026, 5, 11),  # first sale
            (Decimal("60000"), Decimal("20000")),  # split A
            (Decimal("40000"), Decimal("15000")),  # split B
        ]
    )

    async def noop_transaction(db, user_id):
        class Ctx:
            async def __aenter__(self):
                return None

            async def __aexit__(self, *a):
                return None

        return Ctx()

    monkeypatch.setattr(
        "app.ai.deep.period_insights.TenantSession.transaction",
        noop_transaction,
    )

    async def fake_causal(*args, **kwargs):
        from app.ai.deep.period_causes import CausalComparison

        return CausalComparison(
            headline="Внутреннее сравнение: тест",
            bullets=("Причина: объём упал на 33%.",),
        )

    monkeypatch.setattr(
        "app.ai.deep.period_insights.build_causal_comparison",
        fake_causal,
    )

    await _append_period_comparison(
        bullets,
        extras,
        db,  # type: ignore[arg-type]
        uuid4(),
        marketplace=Marketplace.WILDBERRIES,
        period_start=date(2026, 5, 11),
        period_end=date(2026, 5, 20),
        compare_start=date(2026, 5, 1),
        compare_end=date(2026, 5, 10),
    )

    assert extras.get("compare_mode") == "split_fallback"
    assert any("не содержит продаж" in b for b in bullets)
    assert any("объём" in b.lower() or "Причина" in b for b in bullets)
