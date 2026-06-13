"""Governed KPI signals for domain analysts (deterministic; no LLM)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security_context import TenantSession
from app.dto.analytics_dto import TopSKUSummaryDTO
from app.models.economics.sku_unit_economics import SkuUnitEconomicsDaily
from app.models.finance.aggregates import DailyAggregate, SkuDailyMetric
from app.models.report import Marketplace

LOGISTICS_HIGH_SHARE = Decimal("15")
LOGISTICS_SKU_THRESHOLD = Decimal("25")
RETURNS_HIGH_RATE = Decimal("10")
CONCENTRATION_TOP1 = Decimal("50")
CONCENTRATION_TOP3 = Decimal("70")
REVENUE_DROP_THRESHOLD = Decimal("-10")
REVENUE_GROWTH_THRESHOLD = Decimal("10")


async def build_governed_analyst_signals(
    db: AsyncSession,
    user_id: UUID,
    *,
    marketplace: Marketplace,
    period_start: date,
    period_end: date,
    compare_start: date | None = None,
    compare_end: date | None = None,
    total_revenue: Decimal,
    top_skus: list[TopSKUSummaryDTO],
) -> dict:
    """Populate metrics_snapshot fields consumed by build_analytical_package()."""
    out: dict = {}
    if total_revenue <= 0:
        return out

    async with TenantSession.transaction(db, user_id):
        logistics, returns_amount = await _burden_totals(
            db, user_id, marketplace, period_start, period_end
        )
        logistics_share = (logistics / total_revenue * Decimal("100")).quantize(Decimal("0.1"))
        out["logistics_share_pct"] = str(logistics_share)
        if returns_amount > 0:
            return_rate = (returns_amount / total_revenue * Decimal("100")).quantize(Decimal("0.1"))
            out["return_rate_pct"] = str(return_rate)

        out["logistics_high_burden_skus"] = [
            {"sku": sku, "share_pct": str(share), "amount": str(amount)}
            for sku, share, amount in await _high_burden_skus(
                db, user_id, marketplace, period_start, period_end, field="logistics"
            )
        ]
        out["return_top_skus"] = [
            {"sku": sku, "share_pct": str(share), "amount": str(amount)}
            for sku, share, amount in await _top_return_skus(
                db, user_id, marketplace, period_start, period_end
            )
        ]

        if top_skus:
            top1 = top_skus[0].revenue or Decimal("0")
            top3 = sum((s.revenue or Decimal("0")) for s in top_skus[:3])
            out["top1_share_pct"] = str((top1 / total_revenue * Decimal("100")).quantize(Decimal("0.1")))
            out["top3_share_pct"] = str((top3 / total_revenue * Decimal("100")).quantize(Decimal("0.1")))
            out["concentration_top_skus"] = [s.internal_sku for s in top_skus[:3]]

        if compare_start and compare_end:
            cmp_rev, cmp_profit = await _period_totals(
                db, user_id, marketplace, compare_start, compare_end
            )
            if cmp_rev > 0:
                rev_chg = ((total_revenue - cmp_rev) / cmp_rev * Decimal("100")).quantize(Decimal("0.1"))
                out["revenue_change_pct"] = str(rev_chg)
                out["compare_available"] = True
            if cmp_profit != 0:
                prof_chg = ((await _period_profit(db, user_id, marketplace, period_start, period_end) - cmp_profit) / abs(cmp_profit) * Decimal("100")).quantize(Decimal("0.1"))
                out["profit_change_pct"] = str(prof_chg)

            cmp_logistics, cmp_returns = await _burden_totals(
                db, user_id, marketplace, compare_start, compare_end
            )
            if cmp_rev > 0:
                cmp_log_share = cmp_logistics / cmp_rev * Decimal("100")
                out["logistics_share_delta_pp"] = str(
                    (logistics_share - cmp_log_share).quantize(Decimal("0.1"))
                )
                if cmp_returns > 0:
                    cmp_ret_rate = cmp_returns / cmp_rev * Decimal("100")
                    cur_ret = Decimal(out.get("return_rate_pct") or "0")
                    out["return_rate_delta_pp"] = str(
                        (cur_ret - cmp_ret_rate).quantize(Decimal("0.1"))
                    )

            out["sku_revenue_drivers"] = [
                {"sku": sku, "share_pct": str(pct), "amount": str(delta)}
                for sku, pct, delta in await _sku_revenue_drivers(
                    db,
                    user_id,
                    marketplace,
                    period_start,
                    period_end,
                    compare_start,
                    compare_end,
                )
            ]

        out.update(
            await _coverage_signals(
                db, user_id, marketplace, period_start, period_end, total_revenue
            )
        )

    return out


async def _coverage_signals(
    db: AsyncSession,
    user_id: UUID,
    marketplace: Marketplace,
    period_start: date,
    period_end: date,
    total_revenue: Decimal,
) -> dict:
    from app.models.inventory.snapshot import WarehouseStockSnapshot

    econ = (
        await db.execute(
            select(
                func.coalesce(func.sum(SkuUnitEconomicsDaily.commissions), 0),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.storage), 0),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.deductions), 0),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.penalties), 0),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.ads), 0),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.returns_amount), 0),
            ).where(
                SkuUnitEconomicsDaily.user_id == user_id,
                SkuUnitEconomicsDaily.marketplace == marketplace,
                SkuUnitEconomicsDaily.metric_date >= period_start,
                SkuUnitEconomicsDaily.metric_date <= period_end,
            )
        )
    ).one()
    commissions, storage, deductions, penalties, ads, returns_amt = econ

    agg = (
        await db.execute(
            select(
                func.coalesce(func.sum(DailyAggregate.units_sold), 0),
                func.avg(DailyAggregate.average_check),
            ).where(
                DailyAggregate.user_id == user_id,
                DailyAggregate.marketplace == marketplace,
                DailyAggregate.aggregate_date >= period_start,
                DailyAggregate.aggregate_date <= period_end,
            )
        )
    ).one()
    units, avg_check = agg

    inv_count = (
        await db.execute(
            select(func.count())
            .select_from(WarehouseStockSnapshot)
            .where(
                WarehouseStockSnapshot.user_id == user_id,
                WarehouseStockSnapshot.snapshot_date >= period_start,
                WarehouseStockSnapshot.snapshot_date <= period_end,
            )
        )
    ).scalar_one()

    out: dict = {
        "returns_amount": str(Decimal(returns_amt)),
        "units_sold": int(units or 0),
        "ad_spend_available": Decimal(ads) > 0,
        "ad_spend_total": str(Decimal(ads)),
        "inventory_signals_available": int(inv_count or 0) > 0,
        "deductions_total": str(Decimal(deductions)),
        "penalties_total": str(Decimal(penalties)),
    }
    if total_revenue > 0:
        out["commission_share_pct"] = str(
            (Decimal(commissions) / total_revenue * Decimal("100")).quantize(Decimal("0.1"))
        )
        out["storage_share_pct"] = str(
            (Decimal(storage) / total_revenue * Decimal("100")).quantize(Decimal("0.1"))
        )
    if avg_check is not None:
        out["average_check"] = str(Decimal(avg_check).quantize(Decimal("0.01")))

    from app.domain.inventory.intelligence import (
        build_inventory_intelligence,
        inventory_intelligence_to_snapshot,
    )

    inv_intel = await build_inventory_intelligence(
        db,
        user_id,
        marketplace=marketplace,
        period_start=period_start,
        period_end=period_end,
        total_revenue=total_revenue,
    )
    out.update(inventory_intelligence_to_snapshot(inv_intel))
    if inv_intel.inventory_signals_available:
        out["inventory_signals_available"] = True
    return out


async def _period_totals(
    db: AsyncSession, user_id: UUID, marketplace: Marketplace, start: date, end: date
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


async def _period_profit(
    db: AsyncSession, user_id: UUID, marketplace: Marketplace, start: date, end: date
) -> Decimal:
    _, profit = await _period_totals(db, user_id, marketplace, start, end)
    return profit


async def _burden_totals(
    db: AsyncSession, user_id: UUID, marketplace: Marketplace, start: date, end: date
) -> tuple[Decimal, Decimal]:
    row = (
        await db.execute(
            select(
                func.coalesce(func.sum(SkuUnitEconomicsDaily.logistics), 0),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.returns_amount), 0),
            ).where(
                SkuUnitEconomicsDaily.user_id == user_id,
                SkuUnitEconomicsDaily.marketplace == marketplace,
                SkuUnitEconomicsDaily.metric_date >= start,
                SkuUnitEconomicsDaily.metric_date <= end,
            )
        )
    ).one()
    return Decimal(row[0]), Decimal(row[1])


async def _high_burden_skus(
    db: AsyncSession,
    user_id: UUID,
    marketplace: Marketplace,
    start: date,
    end: date,
    *,
    field: str,
    threshold: Decimal = LOGISTICS_SKU_THRESHOLD,
    limit: int = 3,
) -> list[tuple[str, Decimal, Decimal]]:
    burden_col = SkuUnitEconomicsDaily.logistics if field == "logistics" else SkuUnitEconomicsDaily.commissions
    rows = (
        await db.execute(
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
    ).all()
    out: list[tuple[str, Decimal, Decimal]] = []
    for r in rows:
        rev = Decimal(r.revenue)
        burden = Decimal(r.burden)
        if rev <= 0:
            continue
        share = (burden / rev * Decimal("100")).quantize(Decimal("0.1"))
        if share >= threshold:
            out.append((str(r.sku), share, burden))
    out.sort(key=lambda x: x[1], reverse=True)
    return out[:limit]


async def _top_return_skus(
    db: AsyncSession,
    user_id: UUID,
    marketplace: Marketplace,
    start: date,
    end: date,
    limit: int = 3,
) -> list[tuple[str, Decimal, Decimal]]:
    rows = (
        await db.execute(
            select(
                SkuUnitEconomicsDaily.sku,
                func.coalesce(func.sum(SkuUnitEconomicsDaily.revenue), 0).label("revenue"),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.returns_amount), 0).label("returns"),
            )
            .where(
                SkuUnitEconomicsDaily.user_id == user_id,
                SkuUnitEconomicsDaily.marketplace == marketplace,
                SkuUnitEconomicsDaily.metric_date >= start,
                SkuUnitEconomicsDaily.metric_date <= end,
            )
            .group_by(SkuUnitEconomicsDaily.sku)
            .having(func.coalesce(func.sum(SkuUnitEconomicsDaily.returns_amount), 0) > 0)
            .order_by(func.sum(SkuUnitEconomicsDaily.returns_amount).desc())
            .limit(limit)
        )
    ).all()
    out: list[tuple[str, Decimal, Decimal]] = []
    for r in rows:
        rev = Decimal(r.revenue)
        ret = Decimal(r.returns)
        share = (ret / rev * Decimal("100")).quantize(Decimal("0.1")) if rev > 0 else Decimal("0")
        out.append((str(r.sku), share, ret))
    return out


async def _sku_revenue_drivers(
    db: AsyncSession,
    user_id: UUID,
    marketplace: Marketplace,
    period_start: date,
    period_end: date,
    compare_start: date,
    compare_end: date,
    limit: int = 3,
) -> list[tuple[str, Decimal, Decimal]]:
    cur = await _sku_revenue_map(db, user_id, marketplace, period_start, period_end)
    prev = await _sku_revenue_map(db, user_id, marketplace, compare_start, compare_end)
    skus = set(cur) | set(prev)
    deltas: list[tuple[str, Decimal, Decimal]] = []
    for sku in skus:
        delta = cur.get(sku, Decimal("0")) - prev.get(sku, Decimal("0"))
        if delta == 0:
            continue
        base = prev.get(sku, Decimal("0"))
        pct = (delta / base * Decimal("100")).quantize(Decimal("0.1")) if base > 0 else Decimal("100")
        deltas.append((sku, pct, delta))
    deltas.sort(key=lambda x: abs(x[2]), reverse=True)
    return deltas[:limit]


async def _sku_revenue_map(
    db: AsyncSession, user_id: UUID, marketplace: Marketplace, start: date, end: date
) -> dict[str, Decimal]:
    rows = (
        await db.execute(
            select(
                SkuDailyMetric.sku,
                func.coalesce(func.sum(SkuDailyMetric.revenue), 0),
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
    return {str(r[0]): Decimal(r[1]) for r in rows}
