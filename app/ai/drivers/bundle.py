"""Orchestrate driver cards + period decision for action_plan persistence."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.drivers.cards import build_driver_card
from app.ai.drivers.decision import data_first_override, select_simple_decision
from app.ai.drivers.sku_factors import (
    DominantFactor,
    compute_factor_deltas,
    detect_dominant_factor,
    dominant_from_static,
    fetch_sku_period_metrics,
    parse_period_bounds,
)
from app.dto.ai_analytics_dto import GroundedContextDTO, ValidatedInsightDTO
from app.dto.analytics_dto import AIInsightInputDTO
from app.models.report import Marketplace

_ENGINE_VERSION = "6.8.2-mvp"
_MAX_CARDS = 3


def _dec(val: object) -> Decimal:
    if val is None:
        return Decimal("0")
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal("0")


def _marketplace_from_insight(insight: AIInsightInputDTO | None) -> Marketplace | None:
    if insight is None:
        return None
    try:
        return Marketplace(insight.context.marketplace_type)
    except ValueError:
        return None


def _signal_rows(snap: dict, key: str) -> list[dict]:
    raw = snap.get(key)
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, dict) and x.get("sku")]


async def _cards_from_compare(
    db: AsyncSession,
    user_id: UUID,
    *,
    marketplace: Marketplace,
    period_start: date,
    period_end: date,
    compare_start: date,
    compare_end: date,
) -> list[dict]:
    metrics_list = await fetch_sku_period_metrics(
        db,
        user_id,
        marketplace=marketplace,
        period_start=period_start,
        period_end=period_end,
        compare_start=compare_start,
        compare_end=compare_end,
        limit=_MAX_CARDS,
    )
    if not metrics_list:
        return []

    total_loss = sum(abs(m.profit_delta) for m in metrics_list if m.profit_delta < 0)
    if total_loss <= 0:
        total_loss = sum(abs(m.revenue_delta) for m in metrics_list if m.revenue_delta < 0)

    cards: list[dict] = []
    for rank, m in enumerate(metrics_list[:_MAX_CARDS], start=1):
        factors = await compute_factor_deltas(
            db,
            user_id,
            marketplace=marketplace,
            sku=m.sku,
            period_start=period_start,
            period_end=period_end,
            compare_start=compare_start,
            compare_end=compare_end,
            metrics=m,
        )
        if factors is None:
            continue
        dominant = detect_dominant_factor(factors)
        share = None
        if total_loss > 0:
            base = abs(m.profit_delta) if m.profit_delta < 0 else abs(m.revenue_delta)
            share = round(float(base / total_loss * 100), 1) if base else None
        cards.append(
            build_driver_card(
                sku=m.sku,
                dominant=dominant,
                factors=factors,
                rank=rank,
                impact_share_pct=share,
            )
        )
    return cards


def _cards_from_snapshot(snap: dict) -> list[dict]:
    """Static burden / return signals when compare is unavailable."""
    seen: set[str] = set()
    candidates: list[tuple[str, str, Decimal, Decimal]] = []

    for row in _signal_rows(snap, "logistics_high_burden_skus"):
        sku = str(row["sku"])
        if sku in seen:
            continue
        seen.add(sku)
        candidates.append((sku, "logistics", _dec(row.get("amount")), _dec(row.get("share_pct"))))

    for row in _signal_rows(snap, "return_top_skus"):
        sku = str(row["sku"])
        if sku in seen:
            continue
        seen.add(sku)
        candidates.append((sku, "returns", _dec(row.get("amount")), _dec(row.get("share_pct"))))

    for row in _signal_rows(snap, "sku_revenue_drivers"):
        sku = str(row["sku"])
        amount = _dec(row.get("amount"))
        if sku in seen or amount >= 0:
            continue
        seen.add(sku)
        candidates.append((sku, "volume", abs(amount), _dec(row.get("share_pct"))))

    candidates.sort(key=lambda x: x[2], reverse=True)
    cards: list[dict] = []
    total = sum(c[2] for c in candidates[:_MAX_CARDS]) or Decimal("1")
    for rank, (sku, driver_type, amount, share_pct) in enumerate(candidates[:_MAX_CARDS], start=1):
        dominant = dominant_from_static(driver_type=driver_type, amount=amount, share_pct=share_pct)
        impact = round(float(amount / total * 100), 1) if total else None
        cards.append(
            build_driver_card(
                sku=sku,
                dominant=dominant,
                factors=None,
                rank=rank,
                impact_share_pct=impact,
                static_metric=-amount if driver_type != "returns" else -amount,
            )
        )
    return cards


async def build_driver_bundle(
    db: AsyncSession,
    user_id: UUID,
    *,
    grounded: GroundedContextDTO,
    validated: ValidatedInsightDTO,
    insight_input: AIInsightInputDTO | None = None,
) -> dict:
    snap = dict(grounded.metrics_snapshot or {})
    marketplace = _marketplace_from_insight(insight_input)
    a_start, a_end, b_start, b_end = parse_period_bounds(snap)

    cards: list[dict] = []
    if (
        marketplace is not None
        and a_start
        and a_end
        and b_start
        and b_end
        and snap.get("compare_available")
    ):
        try:
            cards = await _cards_from_compare(
                db,
                user_id,
                marketplace=marketplace,
                period_start=a_start,
                period_end=a_end,
                compare_start=b_start,
                compare_end=b_end,
            )
        except Exception:
            cards = []

    if not cards:
        cards = _cards_from_snapshot(snap)

    override = data_first_override(snap=snap, grounded=grounded, validated=validated, cards=cards)
    period_decision = override if override is not None else select_simple_decision(cards)

    return {
        "driver_cards": cards[:_MAX_CARDS],
        "period_decision": period_decision,
        "driver_engine_version": _ENGINE_VERSION,
    }
