from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class TurnoverResult:
    turnover_ratio: Decimal | None
    turnover_days: Decimal | None


def compute_turnover(*, sold_units: int, avg_stock_units: Decimal | None, period_days: int) -> TurnoverResult:
    """
    Deterministic turnover math.

    turnover_ratio = sold_units / avg_stock_units
    turnover_days  = avg_stock_units / avg_daily_sold_units
    """
    if avg_stock_units is None or avg_stock_units <= 0 or period_days <= 0:
        return TurnoverResult(turnover_ratio=None, turnover_days=None)

    ratio = Decimal(sold_units) / avg_stock_units
    avg_daily_sold = Decimal(sold_units) / Decimal(period_days)
    if avg_daily_sold <= 0:
        return TurnoverResult(turnover_ratio=ratio, turnover_days=None)
    return TurnoverResult(turnover_ratio=ratio, turnover_days=(avg_stock_units / avg_daily_sold))


def days_since(*, as_of: date, last_event: date | None, fallback_start: date) -> int | None:
    if last_event is None:
        return (as_of - fallback_start).days
    return (as_of - last_event).days


def stock_risk_label(*, stock_units: int, sold_units: int, period_days: int, days_since_last_sale: int | None) -> str:
    """
    Simple deterministic label for seller UX: ok|stockout|overstock.
    """
    if stock_units <= 0:
        return "ok"

    if period_days > 0 and sold_units > 0:
        avg_daily_sold_units = sold_units / period_days
        if stock_units <= max(1, int(avg_daily_sold_units)):
            return "stockout"

    if days_since_last_sale is not None and days_since_last_sale >= 30:
        return "overstock"

    return "ok"

