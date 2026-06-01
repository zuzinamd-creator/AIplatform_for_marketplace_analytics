from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.economics.inventory_math import compute_turnover, days_since, stock_risk_label


def test_compute_turnover_ratio_and_days() -> None:
    r = compute_turnover(sold_units=30, avg_stock_units=Decimal("10"), period_days=10)
    assert r.turnover_ratio == Decimal("3")
    # avg_daily_sold=3, avg_stock=10 => 10/3 = 3.333...
    assert r.turnover_days is not None
    assert r.turnover_days.quantize(Decimal("0.01")) == Decimal("3.33")


def test_compute_turnover_handles_zero_sales() -> None:
    r = compute_turnover(sold_units=0, avg_stock_units=Decimal("10"), period_days=10)
    assert r.turnover_ratio == Decimal("0")
    assert r.turnover_days is None


def test_days_since_fallback_when_no_last_event() -> None:
    assert days_since(as_of=date(2026, 1, 10), last_event=None, fallback_start=date(2026, 1, 1)) == 9


def test_stock_risk_labels() -> None:
    assert stock_risk_label(stock_units=0, sold_units=10, period_days=10, days_since_last_sale=1) == "ok"
    assert stock_risk_label(stock_units=1, sold_units=20, period_days=10, days_since_last_sale=1) == "stockout"
    assert stock_risk_label(stock_units=100, sold_units=0, period_days=10, days_since_last_sale=40) == "overstock"
