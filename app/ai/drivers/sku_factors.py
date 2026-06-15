"""SKU factor deltas for driver cards (reads existing aggregates; no new tables)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.economics.sku_unit_economics import SkuUnitEconomicsDaily
from app.models.finance.aggregates import SkuDailyMetric
from app.models.report import Marketplace

_FACTOR_KEYS = (
    "commissions",
    "logistics",
    "returns_amount",
    "cogs",
    "ads",
    "storage",
)


@dataclass(frozen=True)
class SkuPeriodMetrics:
    sku: str
    revenue_delta: Decimal
    profit_delta: Decimal
    units_delta: int
    revenue_a: Decimal
    revenue_b: Decimal
    units_a: int
    units_b: int


@dataclass(frozen=True)
class FactorDeltas:
    sku: str
    commissions_delta: Decimal
    logistics_delta: Decimal
    returns_delta: Decimal
    cogs_delta: Decimal
    price_a: Decimal | None
    price_b: Decimal | None
    price_delta: Decimal | None
    units_delta: int
    profit_delta: Decimal
    revenue_delta: Decimal


@dataclass(frozen=True)
class DominantFactor:
    driver_type: str
    factor_delta: Decimal
    confidence: str


def _dec(val: object) -> Decimal:
    if val is None:
        return Decimal("0")
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal("0")


def _parse_date(val: object) -> date | None:
    if val is None:
        return None
    if isinstance(val, date):
        return val
    try:
        return date.fromisoformat(str(val)[:10])
    except ValueError:
        return None


async def fetch_sku_period_metrics(
    db: AsyncSession,
    user_id: UUID,
    *,
    marketplace: Marketplace,
    period_start: date,
    period_end: date,
    compare_start: date,
    compare_end: date,
    limit: int = 5,
) -> list[SkuPeriodMetrics]:
    async def _by_period(start: date, end: date) -> dict[str, tuple[Decimal, Decimal, int]]:
        rows = (
            await db.execute(
                select(
                    SkuDailyMetric.sku,
                    func.coalesce(func.sum(SkuDailyMetric.revenue), 0),
                    func.coalesce(func.sum(SkuDailyMetric.net_profit), 0),
                    func.coalesce(func.sum(SkuDailyMetric.units_sold), 0),
                )
                .where(
                    SkuDailyMetric.user_id == user_id,
                    SkuDailyMetric.marketplace == marketplace,
                    SkuDailyMetric.metric_date >= start,
                    SkuDailyMetric.metric_date <= end,
                )
                .group_by(SkuDailyMetric.sku)
            )
        ).all()
        return {str(r.sku): (Decimal(r[1]), Decimal(r[2]), int(r[3])) for r in rows}

    a_map = await _by_period(period_start, period_end)
    b_map = await _by_period(compare_start, compare_end)
    out: list[SkuPeriodMetrics] = []
    for sku in set(a_map) | set(b_map):
        ra, pa, ua = a_map.get(sku, (Decimal("0"), Decimal("0"), 0))
        rb, pb, ub = b_map.get(sku, (Decimal("0"), Decimal("0"), 0))
        out.append(
            SkuPeriodMetrics(
                sku=sku,
                revenue_delta=ra - rb,
                profit_delta=pa - pb,
                units_delta=ua - ub,
                revenue_a=ra,
                revenue_b=rb,
                units_a=ua,
                units_b=ub,
            )
        )
    out.sort(key=lambda d: d.profit_delta)
    losers = [d for d in out if d.profit_delta < -500][:limit]
    if losers:
        return losers
    out.sort(key=lambda d: d.revenue_delta)
    return [d for d in out if d.revenue_delta < -500][:limit] or out[:limit]


async def compute_factor_deltas(
    db: AsyncSession,
    user_id: UUID,
    *,
    marketplace: Marketplace,
    sku: str,
    period_start: date,
    period_end: date,
    compare_start: date,
    compare_end: date,
    metrics: SkuPeriodMetrics | None = None,
) -> FactorDeltas | None:
    async def _econ_sum(start: date, end: date) -> dict[str, Decimal]:
        row = (
            await db.execute(
                select(
                    func.coalesce(func.sum(SkuUnitEconomicsDaily.revenue), 0),
                    func.coalesce(func.sum(SkuUnitEconomicsDaily.commissions), 0),
                    func.coalesce(func.sum(SkuUnitEconomicsDaily.logistics), 0),
                    func.coalesce(func.sum(SkuUnitEconomicsDaily.returns_amount), 0),
                    func.coalesce(func.sum(SkuUnitEconomicsDaily.cogs), 0),
                    func.coalesce(func.sum(SkuUnitEconomicsDaily.ads), 0),
                    func.coalesce(func.sum(SkuUnitEconomicsDaily.units_sold), 0),
                ).where(
                    SkuUnitEconomicsDaily.user_id == user_id,
                    SkuUnitEconomicsDaily.marketplace == marketplace,
                    SkuUnitEconomicsDaily.sku == sku,
                    SkuUnitEconomicsDaily.metric_date >= start,
                    SkuUnitEconomicsDaily.metric_date <= end,
                )
            )
        ).one()
        keys = ("revenue", "commissions", "logistics", "returns_amount", "cogs", "ads", "units")
        return {keys[i]: Decimal(row[i]) for i in range(len(keys))}

    a = await _econ_sum(period_start, period_end)
    b = await _econ_sum(compare_start, compare_end)

    if metrics is None:
        ua = int(a["units"])
        ub = int(b["units"])
        metrics = SkuPeriodMetrics(
            sku=sku,
            revenue_delta=a["revenue"] - b["revenue"],
            profit_delta=Decimal("0"),
            units_delta=ua - ub,
            revenue_a=a["revenue"],
            revenue_b=b["revenue"],
            units_a=ua,
            units_b=ub,
        )

    price_a = (a["revenue"] / Decimal(a["units"])).quantize(Decimal("0.01")) if a["units"] > 0 else None
    price_b = (b["revenue"] / Decimal(b["units"])).quantize(Decimal("0.01")) if b["units"] > 0 else None
    price_delta = None
    if price_a is not None and price_b is not None and price_b > 0:
        price_delta = price_a - price_b

    return FactorDeltas(
        sku=sku,
        commissions_delta=a["commissions"] - b["commissions"],
        logistics_delta=a["logistics"] - b["logistics"],
        returns_delta=a["returns_amount"] - b["returns_amount"],
        cogs_delta=a["cogs"] - b["cogs"],
        price_a=price_a,
        price_b=price_b,
        price_delta=price_delta,
        units_delta=metrics.units_delta,
        profit_delta=metrics.profit_delta,
        revenue_delta=metrics.revenue_delta,
    )


def detect_dominant_factor(factors: FactorDeltas) -> DominantFactor:
    """Pick commission/logistics/returns/price/volume from factor deltas."""
    impact_base = abs(factors.profit_delta) if factors.profit_delta != 0 else abs(factors.revenue_delta)
    if impact_base < Decimal("1"):
        impact_base = Decimal("1000")

    cost_deltas: list[tuple[str, Decimal]] = [
        ("commission", factors.commissions_delta),
        ("logistics", factors.logistics_delta),
        ("returns", factors.returns_delta),
    ]
    positive_costs = [(t, d) for t, d in cost_deltas if d > 0]
    if positive_costs:
        positive_costs.sort(key=lambda x: x[1], reverse=True)
        driver_type, delta = positive_costs[0]
        share = float(delta / impact_base) if impact_base else 0.0
        confidence = "confirmed" if delta >= Decimal("300") and share >= 0.25 else "probable"
        return DominantFactor(driver_type=driver_type, factor_delta=delta, confidence=confidence)

    if factors.price_delta is not None and factors.price_b and factors.price_b > 0:
        pct = (factors.price_delta / factors.price_b * Decimal("100")).quantize(Decimal("0.1"))
        if pct <= Decimal("-3"):
            return DominantFactor(
                driver_type="price",
                factor_delta=abs(factors.price_delta * Decimal(max(factors.units_a, 1))),
                confidence="probable",
            )

    if factors.units_delta < -3 and abs(factors.revenue_delta) >= impact_base * Decimal("0.25"):
        return DominantFactor(
            driver_type="volume",
            factor_delta=Decimal(abs(factors.units_delta)),
            confidence="probable",
        )

    if factors.commissions_delta > 0:
        return DominantFactor(driver_type="commission", factor_delta=factors.commissions_delta, confidence="probable")
    if factors.logistics_delta > 0:
        return DominantFactor(driver_type="logistics", factor_delta=factors.logistics_delta, confidence="probable")
    if factors.returns_delta > 0:
        return DominantFactor(driver_type="returns", factor_delta=factors.returns_delta, confidence="probable")

    return DominantFactor(driver_type="volume", factor_delta=Decimal("0"), confidence="check_only")


def dominant_from_static(
    *,
    driver_type: str,
    amount: Decimal,
    share_pct: Decimal,
) -> DominantFactor:
    confidence = "confirmed" if share_pct >= Decimal("20") else "probable"
    return DominantFactor(driver_type=driver_type, factor_delta=amount, confidence=confidence)


def parse_period_bounds(snap: dict) -> tuple[date | None, date | None, date | None, date | None]:
    a_start = _parse_date(snap.get("source_period_start"))
    a_end = _parse_date(snap.get("source_period_end"))
    b_start = _parse_date(snap.get("compare_period_start") or snap.get("requested_compare_period_start"))
    b_end = _parse_date(snap.get("compare_period_end") or snap.get("requested_compare_period_end"))
    return a_start, a_end, b_start, b_end
