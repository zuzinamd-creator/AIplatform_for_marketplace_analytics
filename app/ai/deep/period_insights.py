"""Deterministic deep period insights — SKU-level signals beyond dashboard totals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.deep.period_causes import build_causal_comparison
from app.core.security_context import TenantSession
from app.models.economics.sku_unit_economics import SkuUnitEconomicsDaily
from app.models.finance.aggregates import DailyAggregate, SkuDailyMetric
from app.models.report import Marketplace


@dataclass(frozen=True)
class DeepPeriodInsights:
    bullets: tuple[str, ...]
    extras: dict


async def build_deep_period_insights(
    db: AsyncSession,
    user_id: UUID,
    *,
    marketplace: Marketplace,
    period_start: date,
    period_end: date,
    compare_start: date | None = None,
    compare_end: date | None = None,
    cost_coverage_pct: Decimal | None = None,
    missing_cost_skus: list[str] | None = None,
) -> DeepPeriodInsights:
    """SKU-level actionable signals for AI (Russian, deterministic)."""
    bullets: list[str] = []
    extras: dict = {
        "source_period_start": period_start.isoformat(),
        "source_period_end": period_end.isoformat(),
    }
    if cost_coverage_pct is not None:
        extras["cost_coverage_pct"] = str(cost_coverage_pct)

    async with TenantSession.transaction(db, user_id):
        if compare_start and compare_end:
            extras["requested_compare_period_start"] = compare_start.isoformat()
            extras["requested_compare_period_end"] = compare_end.isoformat()
            await _append_period_comparison(
                bullets,
                extras,
                db,
                user_id,
                marketplace,
                period_start,
                period_end,
                compare_start,
                compare_end,
            )

        unprofitable = await _worst_margin_skus(
            db, user_id, marketplace, period_start, period_end, negative_only=True, limit=3
        )
        for sku, rev, profit in unprofitable:
            bullets.append(
                f"Убыточный SKU {sku}: прибыль {profit:.0f} ₽ при выручке {rev:.0f} ₽ — "
                "проверьте себестоимость, логистику и цену."
            )

        logistics_heavy = await _high_burden_skus(
            db, user_id, marketplace, period_start, period_end, field="logistics", threshold=Decimal("0.25")
        )
        for sku, share, amount in logistics_heavy[:2]:
            bullets.append(
                f"Высокая логистика на SKU {sku}: {share:.0%} от выручки ({amount:.0f} ₽) — "
                "рассмотрите упаковку, габариты или перераспределение остатков."
            )

        commission_heavy = await _high_burden_skus(
            db, user_id, marketplace, period_start, period_end, field="commissions", threshold=Decimal("0.20")
        )
        for sku, share, amount in commission_heavy[:2]:
            bullets.append(
                f"Высокая комиссия WB на SKU {sku}: {share:.0%} от выручки ({amount:.0f} ₽) — "
                "проверьте категорию, акции и цену после СПП."
            )

        low_margin = await _worst_margin_skus(
            db, user_id, marketplace, period_start, period_end, negative_only=False, limit=2
        )
        for sku, rev, profit in low_margin:
            if rev <= 0:
                continue
            m = (profit / rev * Decimal("100")).quantize(Decimal("0.1"))
            if m < Decimal("15") and profit >= 0:
                bullets.append(
                    f"Низкая маржа {m}% на SKU {sku} (выручка {rev:.0f} ₽) — "
                    "точка для пересмотра цены или закупочной цены."
                )

        if cost_coverage_pct is not None and cost_coverage_pct < Decimal("100"):
            missing = missing_cost_skus or []
            if missing:
                bullets.append(
                    f"Себестоимость не указана для {len(missing)} SKU с продажами "
                    f"(покрытие {cost_coverage_pct:.0f}%): {', '.join(missing[:5])}"
                    f"{', …' if len(missing) > 5 else ''}."
                )
        elif cost_coverage_pct is not None and cost_coverage_pct >= Decimal("100"):
            extras["cost_data_available"] = True

    return DeepPeriodInsights(bullets=tuple(bullets[:10]), extras=extras)


async def _append_period_comparison(
    bullets: list[str],
    extras: dict,
    db: AsyncSession,
    user_id: UUID,
    marketplace: Marketplace,
    period_start: date,
    period_end: date,
    compare_start: date,
    compare_end: date,
) -> None:
    a_rev, a_profit = await _period_totals(db, user_id, marketplace, period_start, period_end)
    b_rev, b_profit = await _period_totals(db, user_id, marketplace, compare_start, compare_end)

    if b_rev > 0:
        extras["compare_mode"] = "external"
        extras["compare_period_start"] = compare_start.isoformat()
        extras["compare_period_end"] = compare_end.isoformat()
        causal = await build_causal_comparison(
            db,
            user_id,
            marketplace=marketplace,
            period_start=period_start,
            period_end=period_end,
            compare_start=compare_start,
            compare_end=compare_end,
        )
        if causal:
            extras["causal_headline"] = causal.headline
            bullets.extend(causal.bullets)
        return

    first_sale = await _first_sale_date(db, user_id, marketplace)
    note = (
        f"Период сравнения {_fmt_date(compare_start)}—{_fmt_date(compare_end)} не содержит продаж"
    )
    if first_sale:
        note += f" (первая продажа в данных — {_fmt_date(first_sale)})"
    note += "."
    bullets.append(note)

    if a_rev > 0 and (period_end - period_start).days >= 1:
        extras["compare_mode"] = "split_fallback"
        await _append_split_period_compare(
            bullets, extras, db, user_id, marketplace, period_start, period_end
        )
    else:
        extras["compare_mode"] = "no_compare_data"
        bullets.append(
            "Для сравнения выберите два интервала с продажами, например первая и вторая половина мая."
        )


async def _append_split_period_compare(
    bullets: list[str],
    extras: dict,
    db: AsyncSession,
    user_id: UUID,
    marketplace: Marketplace,
    period_start: date,
    period_end: date,
) -> None:
    days = (period_end - period_start).days + 1
    half = max(1, days // 2)
    split_a_end = period_start + timedelta(days=half - 1)
    split_b_start = split_a_end + timedelta(days=1)
    if split_b_start > period_end:
        split_b_start = split_a_end

    rev_a, prof_a = await _period_totals(db, user_id, marketplace, period_start, split_a_end)
    rev_b, prof_b = await _period_totals(db, user_id, marketplace, split_b_start, period_end)

    extras["compare_period_start"] = split_b_start.isoformat()
    extras["compare_period_end"] = period_end.isoformat()
    extras["split_period_a_start"] = period_start.isoformat()
    extras["split_period_a_end"] = split_a_end.isoformat()

    if rev_a <= 0 and rev_b <= 0:
        return

    causal = await build_causal_comparison(
        db,
        user_id,
        marketplace=marketplace,
        period_start=split_b_start,
        period_end=period_end,
        compare_start=period_start,
        compare_end=split_a_end,
        context_prefix="Внутреннее сравнение",
    )
    if causal:
        extras["causal_headline"] = causal.headline
        bullets.extend(causal.bullets)


async def _first_sale_date(
    db: AsyncSession, user_id: UUID, marketplace: Marketplace
) -> date | None:
    row = (
        await db.execute(
            select(func.min(DailyAggregate.aggregate_date)).where(
                DailyAggregate.user_id == user_id,
                DailyAggregate.marketplace == marketplace,
                DailyAggregate.revenue > 0,
            )
        )
    ).scalar_one_or_none()
    return row


def _fmt_date(d: date) -> str:
    return d.strftime("%d.%m.%Y")


async def _period_totals(
    db: AsyncSession,
    user_id: UUID,
    marketplace: Marketplace,
    start: date,
    end: date,
) -> tuple[Decimal, Decimal]:
    row = (
        await db.execute(
            select(
                func.coalesce(func.sum(DailyAggregate.revenue), 0),
                func.coalesce(func.sum(DailyAggregate.net_profit), 0),
            ).where(
                DailyAggregate.user_id == user_id,
                DailyAggregate.marketplace == marketplace,
                DailyAggregate.aggregate_date >= start,
                DailyAggregate.aggregate_date <= end,
            )
        )
    ).one()
    return Decimal(row[0]), Decimal(row[1])


async def _worst_margin_skus(
    db: AsyncSession,
    user_id: UUID,
    marketplace: Marketplace,
    start: date,
    end: date,
    *,
    negative_only: bool,
    limit: int,
) -> list[tuple[str, Decimal, Decimal]]:
    stmt = (
        select(
            SkuDailyMetric.sku,
            func.sum(SkuDailyMetric.revenue).label("revenue"),
            func.sum(SkuDailyMetric.net_profit).label("profit"),
        )
        .where(
            SkuDailyMetric.user_id == user_id,
            SkuDailyMetric.marketplace == marketplace,
            SkuDailyMetric.metric_date >= start,
            SkuDailyMetric.metric_date <= end,
        )
        .group_by(SkuDailyMetric.sku)
        .having(func.sum(SkuDailyMetric.revenue) > 0)
    )
    if negative_only:
        stmt = stmt.having(func.sum(SkuDailyMetric.net_profit) < 0).order_by(
            func.sum(SkuDailyMetric.net_profit).asc()
        )
    else:
        stmt = stmt.order_by(
            (func.sum(SkuDailyMetric.net_profit) / func.sum(SkuDailyMetric.revenue)).asc()
        )
    rows = (await db.execute(stmt.limit(limit))).all()
    return [(str(r.sku), Decimal(r.revenue), Decimal(r.profit)) for r in rows]


async def _high_burden_skus(
    db: AsyncSession,
    user_id: UUID,
    marketplace: Marketplace,
    start: date,
    end: date,
    *,
    field: str,
    threshold: Decimal,
    limit: int = 3,
) -> list[tuple[str, Decimal, Decimal]]:
    burden_col = SkuUnitEconomicsDaily.logistics if field == "logistics" else SkuUnitEconomicsDaily.commissions
    stmt = (
        select(
            SkuUnitEconomicsDaily.sku,
            func.coalesce(func.sum(SkuUnitEconomicsDaily.revenue), 0).label("revenue"),
            func.coalesce(func.sum(burden_col), 0).label("burden"),
        )
        .where(
            SkuUnitEconomicsDaily.user_id == user_id,
            SkuUnitEconomicsDaily.marketplace == marketplace,
            SkuUnitEconomicsDaily.metric_date >= start,
            SkuUnitEconomicsDaily.metric_date <= end,
        )
        .group_by(SkuUnitEconomicsDaily.sku)
        .having(func.coalesce(func.sum(SkuUnitEconomicsDaily.revenue), 0) > 0)
    )
    rows = (await db.execute(stmt)).all()
    out: list[tuple[str, Decimal, Decimal]] = []
    for r in rows:
        rev = Decimal(r.revenue)
        burden = Decimal(r.burden)
        if rev <= 0:
            continue
        share = burden / rev
        if share >= threshold:
            out.append((str(r.sku), share, burden))
    out.sort(key=lambda x: x[1], reverse=True)
    return out[:limit]
