"""Causal explanations for period-over-period changes (Russian, deterministic)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.economics.sku_unit_economics import SkuUnitEconomicsDaily
from app.models.finance.aggregates import DailyAggregate, SkuDailyMetric
from app.models.report import Marketplace

_BUCKET_LABELS: dict[str, str] = {
    "cogs": "себестоимость",
    "commissions": "комиссия WB",
    "logistics": "логистика",
    "storage": "хранение",
    "ads": "реклама",
    "returns_amount": "возвраты",
    "penalties": "штрафы",
    "deductions": "удержания",
}


@dataclass(frozen=True)
class PeriodSnapshot:
    revenue: Decimal
    profit: Decimal
    units: int
    margin_pct: Decimal | None


@dataclass(frozen=True)
class SkuDelta:
    sku: str
    revenue_delta: Decimal
    profit_delta: Decimal
    units_delta: int
    revenue_a: Decimal
    revenue_b: Decimal


@dataclass(frozen=True)
class CausalComparison:
    headline: str
    bullets: tuple[str, ...]


async def build_causal_comparison(
    db: AsyncSession,
    user_id: UUID,
    *,
    marketplace: Marketplace,
    period_start: date,
    period_end: date,
    compare_start: date,
    compare_end: date,
    context_prefix: str = "Сравнение периодов",
) -> CausalComparison | None:
    """Explain *why* KPIs changed between compare (B) and selected (A) period."""
    snap_a = await _period_snapshot(db, user_id, marketplace, period_start, period_end)
    snap_b = await _period_snapshot(db, user_id, marketplace, compare_start, compare_end)
    if snap_b.revenue <= 0:
        return None

    bullets: list[str] = []
    rev_pct = _pct_change(snap_a.revenue, snap_b.revenue)
    prof_pct = _pct_change(snap_a.profit, snap_b.profit) if snap_b.profit != 0 else None

    rev_line = _append_revenue_causes(bullets, snap_a, snap_b, rev_pct)
    prof_line = await _append_profit_causes(
        bullets,
        db,
        user_id,
        marketplace,
        snap_a,
        snap_b,
        prof_pct,
        rev_pct,
        period_start,
        period_end,
        compare_start,
        compare_end,
    )

    headline = prof_line or rev_line
    if not headline:
        direction = "выросла" if rev_pct >= 0 else "упала"
        headline = (
            f"{context_prefix}: выручка {direction} на {abs(rev_pct):.1f}% "
            f"({_fmt(compare_start)}—{_fmt(compare_end)} → {_fmt(period_start)}—{_fmt(period_end)})."
        )

    return CausalComparison(headline=headline[:255], bullets=tuple(bullets[:6]))


def _append_revenue_causes(
    bullets: list[str],
    snap_a: PeriodSnapshot,
    snap_b: PeriodSnapshot,
    rev_pct: Decimal,
) -> str | None:
    if snap_b.units <= 0 or snap_a.units <= 0:
        return None

    avg_b = snap_b.revenue / Decimal(snap_b.units)
    avg_a = snap_a.revenue / Decimal(snap_a.units)
    units_delta = snap_a.units - snap_b.units
    units_pct = (
        (Decimal(units_delta) / Decimal(snap_b.units) * Decimal("100")).quantize(Decimal("0.1"))
        if snap_b.units
        else Decimal("0")
    )

    vol_effect = units_delta * avg_b
    price_effect = Decimal(snap_a.units) * (avg_a - avg_b)
    rev_delta = snap_a.revenue - snap_b.revenue

    direction = "выросла" if rev_pct >= 0 else "упала"
    line = f"Выручка {direction} на {abs(rev_pct):.1f}% ({rev_delta:+.0f} ₽)."

    if abs(units_delta) >= 3 and abs(vol_effect) >= abs(rev_delta) * Decimal("0.25"):
        unit_word = "вырос" if units_delta > 0 else "упал"
        parts = [
            f"Главный фактор — объём: {units_delta:+d} шт ({units_pct:+.1f}%, {unit_word} с {snap_b.units} до {snap_a.units})",
            f"эффект ≈ {vol_effect:+.0f} ₽",
        ]
        if abs(price_effect) >= abs(rev_delta) * Decimal("0.08"):
            check_dir = "вырос" if price_effect > 0 else "снизился"
            parts.append(
                f"средний чек {check_dir} ({avg_b:.0f} → {avg_a:.0f} ₽, эффект {price_effect:+.0f} ₽)"
            )
        bullets.append(f"{line} {'; '.join(parts)}.")
        return bullets[-1][:255]

    if abs(price_effect) >= abs(rev_delta) * Decimal("0.35"):
        check_dir = "вырос" if price_effect > 0 else "снизился"
        bullets.append(
            f"{line} Основной драйвер — средний чек ({avg_b:.0f} → {avg_a:.0f} ₽, "
            f"эффект {price_effect:+.0f} ₽); объём дал {vol_effect:+.0f} ₽."
        )
        return bullets[-1][:255]

    bullets.append(line)
    return None


async def _append_profit_causes(
    bullets: list[str],
    db: AsyncSession,
    user_id: UUID,
    marketplace: Marketplace,
    snap_a: PeriodSnapshot,
    snap_b: PeriodSnapshot,
    prof_pct: Decimal | None,
    rev_pct: Decimal,
    a_start: date,
    a_end: date,
    b_start: date,
    b_end: date,
) -> str | None:
    if snap_b.profit == 0:
        return None

    prof_delta = snap_a.profit - snap_b.profit
    margin_a = _margin(snap_a)
    margin_b = _margin(snap_b)
    prof_fell_more = (
        prof_pct is not None
        and rev_pct < 0
        and prof_pct < rev_pct - Decimal("2")
    ) or (
        prof_pct is not None
        and rev_pct > 0
        and prof_pct < rev_pct - Decimal("2")
    )

    sku_deltas = await _sku_deltas(db, user_id, marketplace, a_start, a_end, b_start, b_end)
    losers = [d for d in sku_deltas if d.profit_delta < -500][:3]
    gainers = [d for d in reversed(sku_deltas) if d.profit_delta > 500][:2]

    if prof_fell_more and margin_a is not None and margin_b is not None:
        margin_gap = margin_a - margin_b
        bucket_line = await _cost_mix_explanation(
            db, user_id, marketplace, a_start, a_end, b_start, b_end, margin_gap
        )
        headline = (
            f"Прибыль изменилась на {prof_delta:+.0f} ₽ ({prof_pct:+.1f}%) при выручке {rev_pct:+.1f}%: "
            f"маржа {margin_b:.1f}% → {margin_a:.1f}% ({margin_gap:+.1f} п.п.)."
        )
        if bucket_line:
            bullets.append(f"{headline} {bucket_line}")
        elif losers:
            sku_part = ", ".join(
                f"{d.sku} ({d.profit_delta:+.0f} ₽"
                f"{f', {d.units_delta:+d} шт' if d.units_delta else ''})"
                for d in losers[:2]
            )
            bullets.append(
                f"{headline} Сжатие маржи из‑за микса SKU, не роста доли логистики/комиссии "
                f"(доли расходов стабильны). Основной минус: {sku_part}."
            )
        else:
            bullets.append(headline)
    elif prof_pct is not None:
        bullets.append(
            f"Прибыль {prof_delta:+.0f} ₽ ({prof_pct:+.1f}%) при выручке {rev_pct:+.1f}%."
        )

    if losers:
        parts = [
            f"{d.sku}: {d.profit_delta:+.0f} ₽"
            + (f", выручка {d.revenue_b:.0f} → {d.revenue_a:.0f} ₽" if d.revenue_b > 0 else "")
            for d in losers[:3]
        ]
        bullets.append(f"SKU с наибольшей просадкой прибыли: {'; '.join(parts)}.")

    if gainers and losers:
        gparts = [f"{d.sku} ({d.profit_delta:+.0f} ₽)" for d in gainers]
        bullets.append(f"Частично компенсировали: {', '.join(gparts)}.")

    top_rev_gainer = max(sku_deltas, key=lambda d: d.revenue_delta, default=None)
    top_prof_loser = min(sku_deltas, key=lambda d: d.profit_delta, default=None)
    if (
        top_rev_gainer
        and top_prof_loser
        and top_rev_gainer.sku != top_prof_loser.sku
        and top_rev_gainer.revenue_delta > 0
        and top_prof_loser.profit_delta < -500
    ):
        bullets.append(
            f"Топ по росту выручки ({top_rev_gainer.sku}, {top_rev_gainer.revenue_delta:+.0f} ₽) "
            f"не компенсирует просадку по {top_prof_loser.sku} ({top_prof_loser.profit_delta:+.0f} ₽) — "
            "смотрите маржу по SKU, а не только оборот."
        )

    for b in bullets:
        if "маржа" in b or "микса SKU" in b or "Прибыль изменилась" in b:
            return b[:255]
    return None


async def _cost_mix_explanation(
    db: AsyncSession,
    user_id: UUID,
    marketplace: Marketplace,
    a_start: date,
    a_end: date,
    b_start: date,
    b_end: date,
    margin_gap: Decimal,
) -> str | None:
    if abs(margin_gap) < Decimal("0.5"):
        return None

    shares_a = await _expense_shares(db, user_id, marketplace, a_start, a_end)
    shares_b = await _expense_shares(db, user_id, marketplace, b_start, b_end)
    if not shares_a or not shares_b:
        return None

    deltas: list[tuple[str, Decimal]] = []
    for key, label in _BUCKET_LABELS.items():
        sa = shares_a.get(key, Decimal("0"))
        sb = shares_b.get(key, Decimal("0"))
        delta_pp = (sa - sb) * Decimal("100")
        if abs(delta_pp) >= Decimal("0.3"):
            deltas.append((label, delta_pp))

    if margin_gap < 0:
        increases = [(label, d) for label, d in deltas if d > 0]
        if increases:
            increases.sort(key=lambda x: x[1], reverse=True)
            parts = [f"{label} +{d:.1f} п.п." for label, d in increases[:2]]
            return f"Маржа сжалась из‑за роста доли расходов: {', '.join(parts)} от выручки."
        return "Доли логистики, комиссии и себестоимости стабильны — сжатие маржи из‑за микса SKU и объёма."

    decreases = [(label, d) for label, d in deltas if d < 0]
    if decreases:
        decreases.sort(key=lambda x: x[1])
        parts = [f"{label} {d:.1f} п.п." for label, d in decreases[:2]]
        return f"Маржа улучшилась за счёт снижения доли: {', '.join(parts)} от выручки."

    return "Доли расходов между периодами почти не изменились."


async def _period_snapshot(
    db: AsyncSession,
    user_id: UUID,
    marketplace: Marketplace,
    start: date,
    end: date,
) -> PeriodSnapshot:
    row = (
        await db.execute(
            select(
                func.coalesce(func.sum(DailyAggregate.revenue), 0),
                func.coalesce(func.sum(DailyAggregate.net_profit), 0),
                func.coalesce(func.sum(DailyAggregate.units_sold), 0),
            ).where(
                DailyAggregate.user_id == user_id,
                DailyAggregate.marketplace == marketplace,
                DailyAggregate.aggregate_date >= start,
                DailyAggregate.aggregate_date <= end,
            )
        )
    ).one()
    rev, prof, units = Decimal(row[0]), Decimal(row[1]), int(row[2])
    margin = (prof / rev * Decimal("100")).quantize(Decimal("0.1")) if rev > 0 else None
    return PeriodSnapshot(revenue=rev, profit=prof, units=units, margin_pct=margin)


async def _expense_shares(
    db: AsyncSession,
    user_id: UUID,
    marketplace: Marketplace,
    start: date,
    end: date,
) -> dict[str, Decimal] | None:
    row = (
        await db.execute(
            select(
                func.coalesce(func.sum(SkuUnitEconomicsDaily.revenue), 0),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.cogs), 0),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.commissions), 0),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.logistics), 0),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.storage), 0),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.ads), 0),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.returns_amount), 0),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.penalties), 0),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.deductions), 0),
            ).where(
                SkuUnitEconomicsDaily.user_id == user_id,
                SkuUnitEconomicsDaily.marketplace == marketplace,
                SkuUnitEconomicsDaily.metric_date >= start,
                SkuUnitEconomicsDaily.metric_date <= end,
            )
        )
    ).one()
    rev = Decimal(row[0])
    if rev <= 0:
        return None
    keys = list(_BUCKET_LABELS.keys())
    return {keys[i]: Decimal(row[i + 1]) / rev for i in range(len(keys))}


async def _sku_deltas(
    db: AsyncSession,
    user_id: UUID,
    marketplace: Marketplace,
    a_start: date,
    a_end: date,
    b_start: date,
    b_end: date,
) -> list[SkuDelta]:
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
        return {
            str(r.sku): (Decimal(r[1]), Decimal(r[2]), int(r[3]))
            for r in rows
        }

    a_map = await _by_period(a_start, a_end)
    b_map = await _by_period(b_start, b_end)
    out: list[SkuDelta] = []
    for sku in set(a_map) | set(b_map):
        ra, pa, ua = a_map.get(sku, (Decimal("0"), Decimal("0"), 0))
        rb, pb, ub = b_map.get(sku, (Decimal("0"), Decimal("0"), 0))
        out.append(
            SkuDelta(
                sku=sku,
                revenue_delta=ra - rb,
                profit_delta=pa - pb,
                units_delta=ua - ub,
                revenue_a=ra,
                revenue_b=rb,
            )
        )
    out.sort(key=lambda d: d.profit_delta)
    return out


def _margin(snap: PeriodSnapshot) -> Decimal | None:
    if snap.revenue <= 0:
        return None
    return (snap.profit / snap.revenue * Decimal("100")).quantize(Decimal("0.1"))


def _pct_change(current: Decimal, baseline: Decimal) -> Decimal:
    if baseline == 0:
        return Decimal("0")
    return ((current - baseline) / abs(baseline) * Decimal("100")).quantize(Decimal("0.1"))


def _fmt(d: date) -> str:
    return d.strftime("%d.%m.%Y")
