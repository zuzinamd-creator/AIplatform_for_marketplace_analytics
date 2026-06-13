"""Inventory Intelligence — derived metrics from existing warehouse snapshots (no new tables)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.economics.inventory_math import compute_turnover, days_since, stock_risk_label
from app.models.cost_history import CostHistory
from app.models.inventory.snapshot import WarehouseStockSnapshot
from app.models.report import Marketplace

SLOW_MOVER_THRESHOLD_DAYS = 30
DEAD_STOCK_THRESHOLD_DAYS = 60
STOCK_CONCENTRATION_HIGH = Decimal("60")
FROZEN_CAPITAL_HIGH_SHARE = Decimal("20")
INVENTORY_RISK_ITEM_THRESHOLD = 3
SEMANTICS_VERSION = "1.0"


@dataclass(frozen=True)
class InventorySkuSignal:
    sku: str
    stock_units: int
    frozen_capital: Decimal | None
    days_since_last_sale: int | None
    share_pct: Decimal = Decimal("0")


@dataclass(frozen=True)
class InventoryIntelligenceResult:
    inventory_signals_available: bool
    turnover_available: bool
    frozen_capital_available: bool
    snapshot_date: date | None
    total_skus: int
    total_frozen_capital: Decimal
    frozen_capital_share_pct: Decimal | None
    slow_mover_count: int
    dead_stock_count: int
    overstock_count: int
    stock_concentration_top3_pct: Decimal | None
    inventory_risk_level: str
    slow_movers: tuple[InventorySkuSignal, ...]
    dead_stock: tuple[InventorySkuSignal, ...]
    top_frozen_capital: tuple[InventorySkuSignal, ...]


async def build_inventory_intelligence(
    db: AsyncSession,
    user_id: UUID,
    *,
    marketplace: Marketplace,
    period_start: date,
    period_end: date,
    total_revenue: Decimal,
    semantics_version: str = SEMANTICS_VERSION,
) -> InventoryIntelligenceResult:
    """Compute inventory intelligence from warehouse_stock_snapshots + cost_history."""
    snapshot_date = await _latest_snapshot_date(
        db, user_id, period_end=period_end, semantics_version=semantics_version
    )
    empty = InventoryIntelligenceResult(
        inventory_signals_available=False,
        turnover_available=False,
        frozen_capital_available=False,
        snapshot_date=None,
        total_skus=0,
        total_frozen_capital=Decimal("0"),
        frozen_capital_share_pct=None,
        slow_mover_count=0,
        dead_stock_count=0,
        overstock_count=0,
        stock_concentration_top3_pct=None,
        inventory_risk_level="low",
        slow_movers=(),
        dead_stock=(),
        top_frozen_capital=(),
    )
    if snapshot_date is None:
        return empty

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
    if not int(inv_count or 0):
        return empty

    stock_stmt = (
        select(
            WarehouseStockSnapshot.sku,
            func.coalesce(func.sum(WarehouseStockSnapshot.actual_stock), 0).label("stock_units"),
        )
        .where(
            WarehouseStockSnapshot.user_id == user_id,
            WarehouseStockSnapshot.snapshot_date == snapshot_date,
            WarehouseStockSnapshot.semantics_version == semantics_version,
            WarehouseStockSnapshot.sku.is_not(None),
        )
        .group_by(WarehouseStockSnapshot.sku)
    )
    stock_rows = (await db.execute(stock_stmt)).all()
    stock_by_sku = {str(sku): int(units or 0) for sku, units in stock_rows}
    if not stock_by_sku:
        return empty

    period_days = max((period_end - period_start).days + 1, 1)
    snap_period_stmt = (
        select(
            WarehouseStockSnapshot.sku,
            func.coalesce(func.sum(WarehouseStockSnapshot.sold_units), 0).label("sold_units"),
            func.avg(WarehouseStockSnapshot.actual_stock).label("avg_stock_units"),
        )
        .where(
            WarehouseStockSnapshot.user_id == user_id,
            WarehouseStockSnapshot.snapshot_date >= period_start,
            WarehouseStockSnapshot.snapshot_date <= period_end,
            WarehouseStockSnapshot.semantics_version == semantics_version,
            WarehouseStockSnapshot.sku.is_not(None),
        )
        .group_by(WarehouseStockSnapshot.sku)
    )
    sold_avg_by_sku: dict[str, tuple[int, Decimal | None]] = {}
    for sku, sold_units, avg_stock in (await db.execute(snap_period_stmt)).all():
        sold_avg_by_sku[str(sku)] = (
            int(sold_units or 0),
            Decimal(avg_stock) if avg_stock is not None else None,
        )

    last_sale_stmt = (
        select(
            WarehouseStockSnapshot.sku,
            func.max(WarehouseStockSnapshot.snapshot_date).label("last_sale_date"),
        )
        .where(
            WarehouseStockSnapshot.user_id == user_id,
            WarehouseStockSnapshot.snapshot_date >= period_start,
            WarehouseStockSnapshot.snapshot_date <= period_end,
            WarehouseStockSnapshot.semantics_version == semantics_version,
            WarehouseStockSnapshot.sku.is_not(None),
            WarehouseStockSnapshot.sold_units > 0,
        )
        .group_by(WarehouseStockSnapshot.sku)
    )
    last_sale_by_sku = {str(sku): d for sku, d in (await db.execute(last_sale_stmt)).all()}

    unit_cost_by_sku = await _unit_costs_as_of(db, user_id, as_of=snapshot_date)

    slow_movers: list[InventorySkuSignal] = []
    dead_stock: list[InventorySkuSignal] = []
    frozen_rows: list[InventorySkuSignal] = []
    overstock_count = 0
    has_turnover = False

    for sku, stock_units in stock_by_sku.items():
        if stock_units <= 0:
            continue
        sold_units, avg_stock = sold_avg_by_sku.get(sku, (0, None))
        turnover = compute_turnover(
            sold_units=sold_units, avg_stock_units=avg_stock, period_days=period_days
        )
        if turnover.turnover_ratio is not None and sold_units > 0:
            has_turnover = True

        unit_cost = unit_cost_by_sku.get(sku)
        frozen = (Decimal(stock_units) * unit_cost) if unit_cost is not None else None

        last_sale = last_sale_by_sku.get(sku)
        days_idle = days_since(
            as_of=snapshot_date, last_event=last_sale, fallback_start=period_start
        )
        risk = stock_risk_label(
            stock_units=stock_units,
            sold_units=sold_units,
            period_days=period_days,
            days_since_last_sale=days_idle,
        )
        if risk == "overstock":
            overstock_count += 1

        signal = InventorySkuSignal(
            sku=sku,
            stock_units=stock_units,
            frozen_capital=frozen,
            days_since_last_sale=days_idle,
        )
        if frozen is not None and frozen > 0:
            frozen_rows.append(signal)

        if days_idle is None:
            continue
        if days_idle >= DEAD_STOCK_THRESHOLD_DAYS:
            dead_stock.append(signal)
        elif days_idle >= SLOW_MOVER_THRESHOLD_DAYS:
            slow_movers.append(signal)

    slow_movers.sort(key=lambda r: (r.frozen_capital or Decimal("-1")), reverse=True)
    dead_stock.sort(key=lambda r: (r.frozen_capital or Decimal("-1")), reverse=True)
    frozen_rows.sort(key=lambda r: (r.frozen_capital or Decimal("-1")), reverse=True)

    total_frozen = sum((r.frozen_capital or Decimal("0")) for r in frozen_rows)
    frozen_share: Decimal | None = None
    if total_revenue > 0 and total_frozen > 0:
        frozen_share = (total_frozen / total_revenue * Decimal("100")).quantize(Decimal("0.1"))

    concentration: Decimal | None = None
    top_frozen: list[InventorySkuSignal] = []
    if total_frozen > 0 and frozen_rows:
        if len(frozen_rows) >= 2:
            top3_sum = sum((r.frozen_capital or Decimal("0")) for r in frozen_rows[:3])
            concentration = (top3_sum / total_frozen * Decimal("100")).quantize(Decimal("0.1"))
        for sig in frozen_rows[:5]:
            share = (
                (sig.frozen_capital or Decimal("0")) / total_frozen * Decimal("100")
            ).quantize(Decimal("0.1"))
            top_frozen.append(
                InventorySkuSignal(
                    sku=sig.sku,
                    stock_units=sig.stock_units,
                    frozen_capital=sig.frozen_capital,
                    days_since_last_sale=sig.days_since_last_sale,
                    share_pct=share,
                )
            )

    risk_level = _inventory_risk_level(
        slow_count=len(slow_movers),
        dead_count=len(dead_stock),
        frozen_share=frozen_share,
        concentration=concentration,
    )

    return InventoryIntelligenceResult(
        inventory_signals_available=True,
        turnover_available=has_turnover,
        frozen_capital_available=total_frozen > 0,
        snapshot_date=snapshot_date,
        total_skus=len(stock_by_sku),
        total_frozen_capital=total_frozen,
        frozen_capital_share_pct=frozen_share,
        slow_mover_count=len(slow_movers),
        dead_stock_count=len(dead_stock),
        overstock_count=overstock_count,
        stock_concentration_top3_pct=concentration,
        inventory_risk_level=risk_level,
        slow_movers=tuple(slow_movers[:5]),
        dead_stock=tuple(dead_stock[:5]),
        top_frozen_capital=tuple(top_frozen),
    )


def inventory_intelligence_to_snapshot(result: InventoryIntelligenceResult) -> dict:
    """Serialize for metrics_snapshot / governed package."""

    def _sku_rows(rows: tuple[InventorySkuSignal, ...]) -> list[dict]:
        return [
            {
                "sku": r.sku,
                "stock_units": r.stock_units,
                "frozen_capital": str(r.frozen_capital) if r.frozen_capital is not None else None,
                "days_since_last_sale": r.days_since_last_sale,
                "share_pct": str(r.share_pct),
            }
            for r in rows
        ]

    out: dict = {
        "inventory_signals_available": result.inventory_signals_available,
        "turnover_available": result.turnover_available,
        "frozen_capital_available": result.frozen_capital_available,
        "inventory_total_skus": result.total_skus,
        "inventory_slow_mover_count": result.slow_mover_count,
        "inventory_dead_stock_count": result.dead_stock_count,
        "inventory_overstock_count": result.overstock_count,
        "inventory_risk_level": result.inventory_risk_level,
        "inventory_slow_movers": _sku_rows(result.slow_movers),
        "inventory_dead_stock": _sku_rows(result.dead_stock),
        "inventory_top_frozen_capital": _sku_rows(result.top_frozen_capital),
    }
    if result.snapshot_date is not None:
        out["inventory_snapshot_date"] = result.snapshot_date.isoformat()
    if result.total_frozen_capital > 0:
        out["inventory_total_frozen_capital"] = str(result.total_frozen_capital.quantize(Decimal("0.01")))
    if result.frozen_capital_share_pct is not None:
        out["inventory_frozen_capital_share_pct"] = str(result.frozen_capital_share_pct)
    if result.stock_concentration_top3_pct is not None:
        out["inventory_stock_concentration_top3_pct"] = str(result.stock_concentration_top3_pct)
    return out


def inventory_deep_bullets(snap: dict) -> list[str]:
    """Deterministic inventory bullets for deep period insights layer."""
    if not snap.get("inventory_signals_available"):
        return []
    bullets: list[str] = []
    dead = int(snap.get("inventory_dead_stock_count") or 0)
    slow = int(snap.get("inventory_slow_mover_count") or 0)
    frozen = snap.get("inventory_total_frozen_capital")
    share = snap.get("inventory_frozen_capital_share_pct")
    conc = snap.get("inventory_stock_concentration_top3_pct")
    if dead:
        bullets.append(
            f"Мёртвый сток: {dead} SKU без продаж {DEAD_STOCK_THRESHOLD_DAYS}+ дней — "
            "замороженный капитал не генерирует выручку."
        )
    if slow:
        bullets.append(
            f"Медленная оборачиваемость: {slow} SKU — снизьте закупку или усильте продвижение."
        )
    if frozen and share:
        bullets.append(
            f"Заморожено {frozen} ₽ в остатках ({share}% выручки) — проверьте закупки и распродажу."
        )
    elif frozen:
        bullets.append(f"Заморожено {frozen} ₽ в остатках — проверьте оборачиваемость по SKU.")
    if conc and Decimal(str(conc)) >= STOCK_CONCENTRATION_HIGH:
        bullets.append(
            f"Концентрация остатков: топ-3 SKU = {conc}% капитала — риск неликвида при просадке спроса."
        )
    return bullets[:4]


def _inventory_risk_level(
    *,
    slow_count: int,
    dead_count: int,
    frozen_share: Decimal | None,
    concentration: Decimal | None,
) -> str:
    if dead_count >= INVENTORY_RISK_ITEM_THRESHOLD:
        return "high"
    if frozen_share is not None and frozen_share >= Decimal("30"):
        return "high"
    if concentration is not None and concentration >= Decimal("70"):
        return "high"
    if slow_count >= INVENTORY_RISK_ITEM_THRESHOLD:
        return "medium"
    if frozen_share is not None and frozen_share >= FROZEN_CAPITAL_HIGH_SHARE:
        return "medium"
    if concentration is not None and concentration >= STOCK_CONCENTRATION_HIGH:
        return "medium"
    if dead_count > 0 or slow_count > 0:
        return "medium"
    return "low"


async def _latest_snapshot_date(
    db: AsyncSession,
    user_id: UUID,
    *,
    period_end: date,
    semantics_version: str,
) -> date | None:
    stmt = (
        select(func.max(WarehouseStockSnapshot.snapshot_date))
        .where(
            WarehouseStockSnapshot.user_id == user_id,
            WarehouseStockSnapshot.snapshot_date <= period_end,
            WarehouseStockSnapshot.semantics_version == semantics_version,
        )
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _unit_costs_as_of(
    db: AsyncSession,
    user_id: UUID,
    *,
    as_of: date,
) -> dict[str, Decimal]:
    max_eff = (
        select(
            CostHistory.internal_sku.label("sku"),
            func.max(CostHistory.effective_from).label("eff"),
        )
        .where(
            CostHistory.user_id == user_id,
            CostHistory.effective_from <= as_of,
            (CostHistory.effective_to.is_(None)) | (CostHistory.effective_to >= as_of),
        )
        .group_by(CostHistory.internal_sku)
        .subquery()
    )
    stmt = select(CostHistory.internal_sku, CostHistory.cost).join(
        max_eff,
        (CostHistory.internal_sku == max_eff.c.sku)
        & (CostHistory.effective_from == max_eff.c.eff)
        & (CostHistory.user_id == user_id),
    )
    return {str(sku): Decimal(cost) for sku, cost in (await db.execute(stmt)).all()}
