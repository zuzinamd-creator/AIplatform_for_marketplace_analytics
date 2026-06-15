"""Simple decision selection and Data First override (MVP)."""

from __future__ import annotations

from decimal import Decimal

from app.ai.drivers.playbook import CAUSE_CONFIDENCE_SCORE, is_pricing_action
from app.dto.ai_analytics_dto import GroundedContextDTO, ValidatedInsightDTO


def _float_cov(snap: dict) -> float | None:
    raw = snap.get("cost_coverage_pct")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def data_first_override(
    *,
    snap: dict,
    grounded: GroundedContextDTO,
    validated: ValidatedInsightDTO,
    cards: list[dict],
) -> dict | None:
    cov = _float_cov(snap)
    has_pricing = any(is_pricing_action(str(c.get("driver_type", ""))) for c in cards)

    if cov is not None and cov < 80 and has_pricing:
        return {
            "mode": "data_first",
            "action": (
                "Сначала загрузите себестоимость по SKU с продажами — "
                "без неё нельзя безопасно менять цену или выходить из акций."
            ),
            "sku": None,
            "driver_type": None,
            "alternative_action": None,
            "data_request": "Загрузите себестоимость в разделе «Себестоимость».",
            "data_request_cta": "costs",
            "source_card_id": None,
            "selection_score": None,
            "blocked_reason": "cost_coverage",
        }

    if grounded.degraded_mode or grounded.rebuild_running_count > 0 or validated.degraded_mode:
        return {
            "mode": "data_first",
            "action": "Дождитесь завершения пересчёта агрегатов — данные могут быть неактуальны.",
            "sku": None,
            "driver_type": None,
            "alternative_action": None,
            "data_request": "Повторите анализ после обновления KPI.",
            "data_request_cta": "rebuild",
            "source_card_id": None,
            "selection_score": None,
            "blocked_reason": "degraded",
        }

    compare_ok = bool(snap.get("compare_available"))
    delta_cards = [c for c in cards if c.get("metric_label") in ("profit_delta", "revenue_delta")]
    if delta_cards and not compare_ok:
        return {
            "mode": "data_first",
            "action": "Включите сравнение с предыдущим периодом — без него нельзя выбрать главный SKU-драйвер.",
            "sku": None,
            "driver_type": None,
            "alternative_action": None,
            "data_request": "Запустите анализ периода с включённым сравнением.",
            "data_request_cta": "compare",
            "source_card_id": None,
            "selection_score": None,
            "blocked_reason": "no_compare",
        }

    return None


def _selection_score(card: dict) -> float:
    conf = CAUSE_CONFIDENCE_SCORE.get(str(card.get("cause_confidence", "probable")), 0.65)
    effect_high = card.get("effect_high_rub") or 0
    try:
        effect = float(effect_high)
    except (TypeError, ValueError):
        effect = 0.0
    if effect <= 0:
        try:
            effect = abs(float(card.get("metric_value_rub") or 0)) * 0.15
        except (TypeError, ValueError):
            effect = 0.0
    return effect * conf


def select_simple_decision(cards: list[dict]) -> dict | None:
    if not cards:
        return None

    ranked = sorted(
        cards,
        key=lambda c: (
            -_selection_score(c),
            -abs(float(c.get("metric_value_rub") or 0)),
            int(c.get("rank") or 99),
        ),
    )
    winner = ranked[0]
    runner = ranked[1] if len(ranked) > 1 else None

    alternative = None
    mode = "single"
    if runner is not None:
        w_score = _selection_score(winner)
        r_score = _selection_score(runner)
        if r_score > 0 and w_score > 0:
            gap = (w_score - r_score) / w_score
            if 0.10 <= gap < 0.20:
                mode = "alternative"
                alternative = str(runner.get("action") or "")

    return {
        "mode": mode,
        "action": str(winner.get("action") or ""),
        "sku": winner.get("sku"),
        "driver_type": winner.get("driver_type"),
        "alternative_action": alternative,
        "data_request": None,
        "data_request_cta": None,
        "source_card_id": winner.get("card_id"),
        "selection_score": round(_selection_score(winner), 2),
        "blocked_reason": None,
    }
