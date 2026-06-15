"""Assemble seller-facing driver card dicts."""

from __future__ import annotations

from decimal import Decimal

from app.ai.drivers.playbook import (
    build_cause_text,
    estimate_effect,
    format_effect_label,
    playbook_action,
    playbook_checks,
)
from app.ai.drivers.sku_factors import DominantFactor, FactorDeltas


def _metric_label_and_value(
    factors: FactorDeltas | None,
    *,
    profit_delta: Decimal | None = None,
    revenue_delta: Decimal | None = None,
) -> tuple[str, Decimal]:
    if factors and factors.profit_delta != 0:
        return "profit_delta", factors.profit_delta
    if factors and factors.revenue_delta != 0:
        return "revenue_delta", factors.revenue_delta
    if profit_delta is not None and profit_delta != 0:
        return "profit_delta", profit_delta
    if revenue_delta is not None and revenue_delta != 0:
        return "revenue_delta", revenue_delta
    return "burden", Decimal("0")


def build_driver_card(
    *,
    sku: str,
    dominant: DominantFactor,
    factors: FactorDeltas | None,
    rank: int,
    impact_share_pct: float | None = None,
    static_metric: Decimal | None = None,
) -> dict:
    driver_type = dominant.driver_type
    metric_label, metric_value = _metric_label_and_value(
        factors,
        profit_delta=static_metric if static_metric and static_metric < 0 else None,
        revenue_delta=static_metric if static_metric and static_metric > 0 else None,
    )
    if static_metric is not None and metric_value == 0:
        metric_value = static_metric
        metric_label = "burden"

    cause = build_cause_text(driver_type, factors, dominant)
    checks = playbook_checks(driver_type)[:3]
    action = playbook_action(driver_type, sku, confidence=dominant.confidence)
    effect_low, effect_high = estimate_effect(
        driver_type,
        dominant.factor_delta,
        static_amount=abs(metric_value) if metric_label == "burden" else None,
    )
    effect_label = format_effect_label(effect_low, effect_high)

    card_id = f"driver:{sku[:32]}:{driver_type}"
    return {
        "card_id": card_id,
        "sku": sku,
        "driver_type": driver_type,
        "metric_label": metric_label,
        "metric_value": str(metric_value.quantize(Decimal("1"))),
        "metric_value_rub": float(metric_value.quantize(Decimal("1"))),
        "impact_share_pct": impact_share_pct,
        "cause": cause,
        "cause_confidence": dominant.confidence,
        "checks": checks,
        "action": action,
        "effect_low_rub": effect_low if effect_low > 0 else None,
        "effect_high_rub": effect_high if effect_high > 0 else None,
        "effect_label": effect_label or None,
        "rank": rank,
    }
