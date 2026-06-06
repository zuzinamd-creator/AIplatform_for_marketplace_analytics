"""Resolve effective-dated cost snapshots by marketplace SKU or internal SKU."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.finance.types import SkuCostSnapshot


def _norm(s: str) -> str:
    return s.strip().casefold()


def build_cost_lookup(
    costs_by_internal_sku: dict[str, list[SkuCostSnapshot]],
    *,
    marketplace_sku_to_internal: dict[str, str] | None = None,
) -> dict[str, list[SkuCostSnapshot]]:
    """
    Index cost history by internal SKU, normalized keys, and marketplace SKU aliases.
    """
    lookup: dict[str, list[SkuCostSnapshot]] = {}
    for internal_sku, snapshots in costs_by_internal_sku.items():
        lookup[internal_sku] = snapshots
        lookup[_norm(internal_sku)] = snapshots

    if marketplace_sku_to_internal:
        for marketplace_sku, internal in marketplace_sku_to_internal.items():
            snaps = costs_by_internal_sku.get(internal)
            if snaps:
                lookup[marketplace_sku] = snaps
                lookup[_norm(marketplace_sku)] = snaps

    return lookup


def resolve_cost_snapshots(lookup: dict[str, list[SkuCostSnapshot]], sku: str | None) -> list[SkuCostSnapshot]:
    if not sku:
        return []
    direct = lookup.get(sku)
    if direct:
        return direct
    return lookup.get(_norm(sku), [])


def unit_cost_on_date(history: list[SkuCostSnapshot], on_date: date) -> Decimal | None:
    applicable = [item for item in history if item.effective_from <= on_date]
    if not applicable:
        return None
    latest = max(applicable, key=lambda item: item.effective_from)
    return latest.total_unit_cost
