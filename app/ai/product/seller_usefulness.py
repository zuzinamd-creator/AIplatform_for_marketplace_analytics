"""Seller-facing usefulness enrichment (deterministic, Russian UI copy)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from app.ai.product.data_gap_advisor import build_data_gap_advice
from app.dto.ai_analytics_dto import GroundedContextDTO, ValidatedInsightDTO
from app.dto.ai_intelligence_dto import ScoredRecommendationDTO


@dataclass(frozen=True)
class SellerUsefulnessDTO:
    why_this_matters: str
    expected_business_impact: str
    urgency: str
    urgency_score: int
    estimated_upside: str
    estimated_downside: str
    concrete_next_action: str
    confidence_explanation: str
    limitations: list[str]
    data_gaps: list[str]


def build_seller_usefulness(
    *,
    scored: ScoredRecommendationDTO,
    validated: ValidatedInsightDTO,
    grounded: GroundedContextDTO,
    flags: list[str],
) -> SellerUsefulnessDTO:
    snap = grounded.metrics_snapshot or {}
    limitations: list[str] = [
        "Совет носит рекомендательный характер — цены, рекламу и остатки нужно менять в кабинете WB вручную.",
        "Цифры основаны на загруженных отчётах, а не на live-API маркететплейса.",
    ]

    urgency_score = 50
    if validated.workflow.value in ("risk_detection", "anomaly_explanation"):
        urgency_score = 85
    elif scored.priority_score >= Decimal("70"):
        urgency_score = 75
    elif scored.priority_score >= Decimal("40"):
        urgency_score = 55
    else:
        urgency_score = 35

    if "stale_or_degraded_context" in flags:
        urgency_score = min(urgency_score, 45)
        limitations.append("Данные могут быть устаревшими — дождитесь пересчёта агрегатов и проверьте KPI.")

    if "no_evidence" in flags:
        limitations.append("Мало ссылок на первоисточник — сверьте цифры на Dashboard перед действиями.")

    urgency = "на этой неделе"
    if urgency_score >= 80:
        urgency = "сегодня"
    elif urgency_score >= 60:
        urgency = "на этой неделе"
    else:
        urgency = "когда будет время"

    why = _pick_why(scored=scored, validated=validated, grounded=grounded)

    impact = "умеренное влияние на прибыль после проверки цифр"
    if urgency_score >= 80:
        impact = "высокое — сначала устраните проблему данных, иначе KPI будут искажены"
    elif urgency_score < 45:
        impact = "низкое — информационная рекомендация"

    upside = "Защита маржи или рост выручки после проверки фактов"
    downside = "Без действий ситуация по SKU и марже может не улучшиться"
    if "stale_or_degraded_context" in flags:
        downside = "Решения по устаревшим KPI могут привести к неверным ценам или закупкам"

    data_gaps = build_data_gap_advice(
        sku_count=int(snap.get("sku_count") or 0),
        total_revenue=_dec(snap.get("total_revenue")),
        total_profit=_dec(snap.get("total_profit")),
        margin=_dec(snap.get("margin")),
        cost_coverage_pct=snap.get("cost_coverage_pct"),
        cost_data_available=bool(snap.get("cost_data_available")),
        inventory_signals=bool(snap.get("inventory_signals_available")),
        ad_spend_available=bool(snap.get("ad_spend_available")),
        anomalies=[str(a) for a in (snap.get("anomaly_messages") or [])],
    )

    action = _pick_action(scored=scored, validated=validated, data_gaps=data_gaps, snap=snap)

    conf_parts = [f"Уверенность модели {scored.confidence:.0%} после проверки данных."]
    if flags:
        conf_parts.append(f"Скорректировано: {', '.join(_flag_label(f) for f in flags)}.")
    if validated.stale_data_warning:
        conf_parts.append("Активно предупреждение об устаревших данных.")

    return SellerUsefulnessDTO(
        why_this_matters=why,
        expected_business_impact=impact,
        urgency=urgency,
        urgency_score=urgency_score,
        estimated_upside=upside,
        estimated_downside=downside,
        concrete_next_action=action[:500],
        confidence_explanation=" ".join(conf_parts),
        limitations=limitations,
        data_gaps=data_gaps,
    )


def _pick_why(
    *,
    scored: ScoredRecommendationDTO,
    validated: ValidatedInsightDTO,
    grounded: GroundedContextDTO,
) -> str:
    snap = grounded.metrics_snapshot or {}
    deep = snap.get("deep_insights") or []
    causal = snap.get("causal_headline")
    if causal:
        return str(causal)[:400]
    if deep:
        for line in deep:
            if _is_causal_insight(str(line)):
                return str(line)[:400]
        return str(deep[0])[:400]

    if validated.workflow.value == "anomaly_explanation":
        return "Ошибки в данных искажают выручку и маржу — сначала исправьте источник."
    for bullet in scored.bullets:
        if bullet and len(bullet) > 20 and _looks_russian(bullet):
            if not _is_dashboard_echo(bullet, snap):
                return bullet[:400]
    if validated.summary and _looks_russian(validated.summary):
        if not _is_dashboard_echo(validated.summary, snap):
            return validated.summary[:400]
    if deep:
        return str(deep[0])[:400]
    rev = snap.get("total_revenue")
    if rev is not None:
        return f"За период {snap.get('source_period_start', '')} — {snap.get('source_period_end', '')} выручка {rev} ₽; см. действия по SKU ниже."
    return "Есть сигнал по KPI периода — откройте детали и сверьте с Dashboard."


def _is_dashboard_echo(text: str, snap: dict) -> bool:
    """Skip generic revenue/profit restatements when deep insights exist."""
    low = text.lower()
    if _is_causal_insight(text):
        return False
    if "общий доход" in low or "общая прибыль" in low:
        rev = str(snap.get("total_revenue") or "")
        if rev and rev[:4] in text.replace(" ", "").replace(",", ""):
            return True
    if "сравнение периодов:" in low and "выручка" in low and "→" in text:
        return True
    return False


def _is_causal_insight(text: str) -> bool:
    low = text.lower()
    markers = (
        "главный фактор",
        "из‑за",
        "из-за",
        "микса sku",
        "маржа",
        "драйвер",
        "компенсировали",
        "просадкой прибыли",
        "п.п.",
        "эффект",
    )
    return any(m in low for m in markers)


def _pick_action(
    *,
    scored: ScoredRecommendationDTO,
    validated: ValidatedInsightDTO,
    data_gaps: list[str],
    snap: dict | None = None,
) -> str:
    snap = snap or {}
    action_verbs = ("проверьте", "сверьте", "рассмотрите", "добавьте", "импортируйте", "загрузите", "оцените", "продвигайте")
    for line in snap.get("analyst_actions") or []:
        if line and any(v in str(line).lower() for v in action_verbs):
            return str(line)[:500]
    for line in snap.get("deep_insights") or []:
        low = str(line).lower()
        if any(v in low for v in action_verbs):
            return str(line)[:500]

    for bullet in scored.bullets[1:]:
        if bullet and len(bullet) > 15:
            low = bullet.lower()
            if any(v in low for v in action_verbs) or re.search(r"sku|артикул", low):
                return bullet[:500]
    if scored.bullets:
        first = scored.bullets[0]
        if first and _is_causal_insight(str(first)):
            return (
                f"{first[:220]} — сверьте цены, остатки и рекламу по указанным SKU в кабинете WB."
            )[:500]
        return first[:500]
    if data_gaps:
        return data_gaps[0]
    return (
        "Откройте детали → сверьте KPI на Dashboard → при необходимости загрузите недостающие данные "
        "→ примените изменение в кабинете WB → отметьте выполненным здесь."
    )


def _dec(val: object) -> Decimal | None:
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except Exception:
        return None


def _looks_russian(text: str) -> bool:
    return any("\u0400" <= c <= "\u04FF" for c in text)


def _flag_label(flag: str) -> str:
    labels = {
        "stale_or_degraded_context": "устаревший контекст",
        "no_evidence": "мало evidence",
        "generic_wording": "общая формулировка",
        "contradictions": "противоречия",
        "unsupported_claims": "неподтверждённые утверждения",
        "fatigue_cooldown": "повтор рекомендации",
        "fatigue_decay": "снижение новизны",
        "fatigue_suppress": "дубликат",
    }
    return labels.get(flag, flag)
