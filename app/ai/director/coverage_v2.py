"""Business Coverage V2 — granular completeness model (Phase 6.3).

V1 counted whole blocks (sales + MP costs + COGS ≈ 50%).
V2 scores each dimension by sub-signal completeness → typically lower and more honest.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CoverageDimension:
    dimension_id: str
    label: str
    weight: int
    completeness: Decimal  # 0..1


@dataclass(frozen=True)
class CoverageV2Result:
    coverage_score: Decimal
    missing_data_score: Decimal
    dimensions: tuple[CoverageDimension, ...]
    formula: str
    missing_blocks: tuple[str, ...]


# Weights sum to 100
_DIMENSION_WEIGHTS: tuple[tuple[str, str, int], ...] = (
    ("sales", "Продажи (выручка, заказы, SKU)", 10),
    ("price", "Цена / средний чек", 8),
    ("promotion", "Продвижение (реклама MP)", 12),
    ("ctr", "CTR / показы / клики", 8),
    ("conversion", "Конверсия карточки", 8),
    ("inventory", "Остатки / оборачиваемость", 10),
    ("marketplace_economics", "Комиссия, логистика, хранение, штрафы", 12),
    ("cogs", "Себестоимость, маржа, ROI", 12),
    ("tax", "Налоги", 10),
    ("opex", "Операционные расходы", 10),
)


def assess_coverage_v2(snap: dict) -> CoverageV2Result:
    dims: list[CoverageDimension] = []

    sales_signals = [
        _has(snap, "total_revenue"),
        int(snap.get("sku_count") or 0) > 0 or _has(snap, "units_sold"),
        _has(snap, "return_rate_pct"),
    ]
    dims.append(_dim("sales", sales_signals))

    price_signals = [_has(snap, "average_check")]
    dims.append(_dim("price", price_signals))

    promo_signals = [bool(snap.get("ad_spend_available"))]
    dims.append(_dim("promotion", promo_signals))

    ctr_signals = [
        bool(snap.get("ad_impressions_available")),
        bool(snap.get("ad_clicks_available")),
        bool(snap.get("ad_ctr_available")),
    ]
    dims.append(_dim("ctr", ctr_signals))

    conv_signals = [bool(snap.get("card_conversion_available")), bool(snap.get("card_ctr_available"))]
    dims.append(_dim("conversion", conv_signals))

    inv_signals = [
        bool(snap.get("inventory_signals_available")),
        bool(snap.get("turnover_available")),
        bool(snap.get("procurement_available")),
    ]
    dims.append(_dim("inventory", inv_signals))

    mp_signals = [
        snap.get("commission_share_pct") is not None,
        snap.get("logistics_share_pct") is not None,
        snap.get("storage_share_pct") is not None,
        _has(snap, "penalties_total"),
    ]
    dims.append(_dim("marketplace_economics", mp_signals))

    cov_pct = _dec(snap.get("cost_coverage_pct"))
    cogs_signals = [
        cov_pct is not None and cov_pct > 0,
        _has(snap, "total_profit"),
        snap.get("margin") is not None and cov_pct is not None and cov_pct >= 100,
        snap.get("roi") is not None,
    ]
    dims.append(_dim("cogs", cogs_signals))

    tax_signals = [
        bool(snap.get("tax_usn_available")),
        bool(snap.get("tax_vat_available")),
        bool(snap.get("tax_insurance_available")),
    ]
    dims.append(_dim("tax", tax_signals))

    opex_signals = [
        bool(snap.get("opex_payroll_available")),
        bool(snap.get("opex_contractors_available")),
        bool(snap.get("opex_rent_available")),
    ]
    dims.append(_dim("opex", opex_signals))

    total_weight = sum(d.weight for d in dims)
    weighted = sum(d.weight * d.completeness for d in dims)
    score = (weighted / Decimal(total_weight) * Decimal("100")).quantize(Decimal("0.1"))
    missing = (Decimal("100") - score).quantize(Decimal("0.1"))

    missing_blocks = tuple(
        d.label for d in dims if d.completeness <= Decimal("0")
    ) + tuple(
        d.label for d in dims if Decimal("0") < d.completeness < Decimal("1")
    )

    formula = (
        "Coverage V2 = Σ(weight × completeness_ratio) / Σ(weights) × 100%; "
        f"completeness_ratio ∈ [0,1] per dimension; "
        f"= {weighted.quantize(Decimal('0.1'))}/{total_weight} × 100% = {score}%"
    )

    return CoverageV2Result(
        coverage_score=score,
        missing_data_score=missing,
        dimensions=tuple(dims),
        formula=formula,
        missing_blocks=missing_blocks,
    )


def _dim(dim_id: str, signals: list[bool]) -> CoverageDimension:
    label = next(l for i, l, _ in _DIMENSION_WEIGHTS if i == dim_id)
    weight = next(w for i, _, w in _DIMENSION_WEIGHTS if i == dim_id)
    ratio = Decimal(sum(1 for s in signals if s)) / Decimal(len(signals) or 1)
    return CoverageDimension(dim_id, label, weight, ratio.quantize(Decimal("0.01")))


def _has(snap: dict, key: str) -> bool:
    val = snap.get(key)
    if val is None:
        return False
    try:
        return Decimal(str(val)) > 0
    except Exception:
        return bool(val)


def _dec(val: object) -> Decimal | None:
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except Exception:
        return None
