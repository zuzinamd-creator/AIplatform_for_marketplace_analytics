"""Phase 6.1 recommendation quality audit helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

from app.ai.insights.quality import (
    StatementKind,
    audit_text_fields,
    classify_statement_kind,
    detect_echo_pattern,
)


class RecommendationClass(StrEnum):
    INSIGHT = "Insight"
    DASHBOARD_ECHO = "Dashboard Echo"
    FALSE_POSITIVE = "False Positive"
    DATA_QUALITY_WARNING = "Data Quality Warning"


@dataclass(frozen=True)
class EchoAnalysis:
    kpis_used: list[str]
    new_insight: str
    beyond_dashboard: bool


@dataclass(frozen=True)
class BusinessCaseRule:
    case_id: str
    label: str
    implemented: bool
    rule: str
    example: str


BUSINESS_CASE_CATALOG: tuple[BusinessCaseRule, ...] = (
    BusinessCaseRule("1", "Высокая логистика", True, "logistics_analyst.logistics_high_share", "Логистика составляет X% выручки…"),
    BusinessCaseRule("2", "Высокая комиссия", True, "deep_period_insights.commission_heavy_sku", "Высокая комиссия WB на SKU…"),
    BusinessCaseRule("3", "Высокие возвраты", True, "returns_analyst.returns_high_rate", "Возвраты X% от выручки…"),
    BusinessCaseRule("4", "Концентрация на одном SKU", True, "concentration_analyst.concentration_top1_risk", "X% выручки приходится на один SKU…"),
    BusinessCaseRule("5", "Резкое падение продаж", True, "revenue_change_analyst.revenue_drop", "Выручка упала на X%…"),
    BusinessCaseRule("6", "Резкое падение прибыли", True, "revenue_change_analyst.profit_drop", "Прибыль упала на X%…"),
    BusinessCaseRule("7", "Отсутствие себестоимости", True, "data_gap_advisor + cost_coverage anomaly", "Импортируйте себестоимость…"),
    BusinessCaseRule("8", "Частичное покрытие себестоимостью", True, "deep_period_insights.missing_cost_skus", "Себестоимость не указана для N SKU…"),
    BusinessCaseRule("9", "Проблемные SKU", True, "deep_period_insights.unprofitable_sku / low_margin", "Убыточный SKU… / Низкая маржа…"),
    BusinessCaseRule("10", "Аномалии периода", True, "anomaly_analyst + period_causes", "Anomaly message / causal comparison"),
)

ANALYST_RULE_CATALOG: dict[str, list[str]] = {
    "logistics_analyst": [
        "logistics_high_share",
        "logistics_share_growth",
        "logistics_sku_anomaly_*",
    ],
    "returns_analyst": [
        "returns_high_rate",
        "returns_rate_growth",
        "returns_sku_leader_*",
    ],
    "revenue_change_analyst": [
        "revenue_drop",
        "revenue_growth",
        "profit_drop",
        "revenue_sku_driver_*",
    ],
    "concentration_analyst": [
        "concentration_top1_risk",
        "concentration_top3_risk",
    ],
    "deep_period_insights": [
        "unprofitable_sku",
        "logistics_heavy_sku",
        "commission_heavy_sku",
        "low_margin_sku",
        "missing_cost_skus",
        "period_comparison",
    ],
    "sales_analyst": ["sales_low_margin", "sales_top_sku", "sales_revenue_present"],
    "funnel_analyst": ["funnel_concentration", "funnel_breadth_ok"],
    "anomaly_analyst": ["anomaly_*"],
}


def classify_recommendation_text(text: str, snap: dict | None = None) -> RecommendationClass:
    snap = snap or {}
    low = text.lower()

    if _is_data_quality_warning(text, snap):
        return RecommendationClass.DATA_QUALITY_WARNING
    if _is_false_positive(text, snap):
        return RecommendationClass.FALSE_POSITIVE
    if is_dashboard_echo(text, snap):
        return RecommendationClass.DASHBOARD_ECHO
    return RecommendationClass.INSIGHT


def is_dashboard_echo(text: str, snap: dict | None = None) -> bool:
    snap = snap or {}
    low = text.lower()

    if _is_structured_insight_block(text):
        return False
    if _is_causal_insight(text):
        return False

    echo = detect_echo_pattern(text, snap)
    if echo.echo_detected:
        return True

    if any(k in low for k in ("sku", "артикул", "логистик", "возврат", "концентрац", "убыточ", "себестоим")):
        if re.search(r"\d", text):
            return False

    rev = str(snap.get("total_revenue") or "").replace(".", ",")
    rev_plain = rev.split(".")[0] if rev else ""
    if rev_plain and len(rev_plain) >= 4:
        digits = re.sub(r"\D", "", text)
        if rev_plain[:5] in digits or rev_plain.replace(",", "")[:5] in digits:
            if not _is_causal_insight(text):
                return True

    echo_phrases = (
        "выручка составила",
        "общий доход",
        "общая прибыль",
        "reported revenue",
        "governed revenue",
        "across",
        "skus (governed",
    )
    if any(p in low for p in echo_phrases):
        return True
    if "сравнение периодов:" in low and "выручка" in low and "→" in text:
        return True
    return False


def analyze_dashboard_echo(text: str, snap: dict | None = None) -> EchoAnalysis:
    snap = snap or {}
    kpis: list[str] = []
    if snap.get("total_revenue") and str(snap.get("total_revenue"))[:4] in re.sub(r"\D", "", text):
        kpis.append("total_revenue")
    if "маржа" in text.lower() or "margin" in text.lower():
        kpis.append("margin")
    if "прибыл" in text.lower() or "profit" in text.lower():
        kpis.append("total_profit")
    if "логистик" in text.lower():
        kpis.append("logistics")
    if "возврат" in text.lower():
        kpis.append("returns")

    beyond = not is_dashboard_echo(text, snap) and bool(_is_causal_insight(text) or "sku" in text.lower())
    insight = text[:200] if beyond else "Пересказ KPI без нового вывода"
    return EchoAnalysis(kpis_used=kpis, new_insight=insight, beyond_dashboard=beyond)


def is_actionable(text: str, recommended_action: str | None = None) -> bool:
    body = " ".join(x for x in (text, recommended_action or "") if x).strip()
    low = body.lower()
    if len(body) < 25:
        return False

    weak_only = (
        low in ("логистика высокая.", "логистика высокая", "маржа низкая.", "выручка упала.")
        or low.startswith("review ")
        or "monitor" in low and len(body) < 60
    )
    if weak_only:
        return False

    has_number = bool(re.search(r"\d", body))
    has_sku = bool(re.search(r"sku|артикул|[A-Za-z]-\d", body, re.I))
    action_verbs = (
        "проверьте",
        "сверьте",
        "загрузите",
        "импортируйте",
        "добавьте",
        "измените",
        "рассмотрите",
        "продвигайте",
        "устраните",
        "оцените",
        "check",
        "verify",
        "upload",
    )
    has_verb = any(v in low for v in action_verbs)
    has_specifics = has_number or has_sku or "—" in body or " - " in body or "→" in body

    if has_verb and (has_specifics or len(body) >= 80):
        return True
    if has_sku and has_number and _is_causal_insight(body):
        return True
    if has_sku and has_verb:
        return True
    return False


def check_period_consistency(
    *,
    ui_start: str | None,
    ui_end: str | None,
    request_start: str | None,
    request_end: str | None,
    snapshot_start: str | None,
    snapshot_end: str | None,
) -> dict[str, Any]:
    fields = {
        "ui": f"{ui_start} — {ui_end}",
        "ai_request": f"{request_start} — {request_end}",
        "kpi_snapshot": f"{snapshot_start} — {snapshot_end}",
    }
    match = (
        bool(ui_start and ui_end)
        and ui_start == request_start == snapshot_start
        and ui_end == request_end == snapshot_end
    )
    return {"fields": fields, "consistent": match}


def compute_mvp_ai_score(
    *,
    insight_rate: float,
    echo_rate: float,
    actionable_rate: float,
    period_consistency_rate: float,
    business_coverage: float,
    seller_usefulness: float | None = None,
) -> dict[str, float]:
    usefulness = seller_usefulness if seller_usefulness is not None else actionable_rate * 100
    accuracy = max(0.0, min(100.0, (1.0 - echo_rate) * 70 + insight_rate * 30))
    explainability = max(0.0, min(100.0, insight_rate * 100))
    actionability = actionable_rate * 100
    trustworthiness = max(
        0.0,
        min(100.0, period_consistency_rate * 40 + (1.0 - echo_rate) * 35 + min(business_coverage, 100.0) * 0.25),
    )
    seller_value = max(
        0.0,
        min(
            100.0,
            usefulness * 0.35
            + actionable_rate * 100 * 0.25
            + min(business_coverage, 100.0) * 0.25
            + insight_rate * 15,
        ),
    )
    cov = min(business_coverage, 100.0)
    total = round(
        accuracy * 0.15
        + explainability * 0.10
        + actionability * 0.20
        + trustworthiness * 0.20
        + seller_value * 0.20
        + cov * 0.15,
        1,
    )
    return {
        "Accuracy": round(accuracy, 1),
        "Explainability": round(explainability, 1),
        "Actionability": round(actionability, 1),
        "Trustworthiness": round(trustworthiness, 1),
        "Seller Value": round(seller_value, 1),
        "Business Coverage": round(cov, 1),
        "Seller Usefulness": round(usefulness, 1),
        "AI Readiness Score": total,
    }


def evaluate_go_no_go(
    *,
    actionable_rate: float,
    seller_usefulness: float,
    echo_rate: float,
    ai_readiness: float,
) -> dict[str, object]:
    checks = {
        "actionable_rate_gte_80": actionable_rate >= 0.8,
        "seller_usefulness_gte_80": seller_usefulness >= 80.0,
        "dashboard_echo_lte_10": echo_rate <= 0.10,
        "ai_readiness_gte_80": ai_readiness >= 80.0,
    }
    return {
        "decision": "GO" if all(checks.values()) else "NO-GO",
        "checks": checks,
    }


def evaluate_go_no_go(
    *,
    actionable_rate: float,
    seller_usefulness: float,
    echo_rate: float,
    ai_readiness: float,
) -> dict[str, object]:
    checks = {
        "actionable_rate_gte_80": actionable_rate >= 0.8,
        "seller_usefulness_gte_80": seller_usefulness >= 80.0,
        "dashboard_echo_lte_10": echo_rate <= 0.10,
        "ai_readiness_gte_80": ai_readiness >= 80.0,
    }
    return {
        "decision": "GO" if all(checks.values()) else "NO-GO",
        "checks": checks,
    }


def audit_insight_statements(
    *,
    title: str,
    summary: str,
    snap: dict | None = None,
    structured_insights: list[dict] | None = None,
    insight_audit: dict | None = None,
    insight_quality: dict | None = None,
) -> dict[str, Any]:
    """Phase 6.2.2 — KPI vs Insight classification and quality rollup."""
    fields = {"title": title, "summary": summary[:800] if summary else ""}
    for idx, ins in enumerate(structured_insights or []):
        block = ins.get("what_happened") or ""
        if ins.get("why"):
            block = f"{block} {ins['why']}"
        if ins.get("recommended_action"):
            block = f"{block} {ins['recommended_action']}"
        fields[f"structured_{idx}"] = block

    text_audit = audit_text_fields(fields, snap)
    if insight_audit:
        text_audit["llm_echo_detected"] = insight_audit.get("llm_echo_detected")
        text_audit["llm_echo_fields"] = insight_audit.get("llm_echo_fields") or []

    quality_scores: list[dict] = []
    for ins in structured_insights or []:
        q = ins.get("insight_quality")
        if isinstance(q, dict) and q.get("overall") is not None:
            quality_scores.append(q)
    if insight_quality and insight_quality.get("overall") is not None:
        quality_scores.append(insight_quality)

    avg_quality: dict[str, float] = {}
    if quality_scores:
        for key in ("causal_depth", "business_relevance", "actionability", "confidence", "overall"):
            vals = [float(q[key]) for q in quality_scores if q.get(key) is not None]
            if vals:
                avg_quality[key] = round(sum(vals) / len(vals), 1)

    return {
        **text_audit,
        "statement_fields_audited": len(fields),
        "insight_quality_avg": avg_quality,
        "structured_insight_count": len(structured_insights or []),
    }


def extract_insight_payload_from_plan(plan: dict) -> dict[str, Any]:
    su = plan.get("seller_usefulness") or plan
    return {
        "insight_engine": plan.get("insight_engine") or su.get("insight_engine") or {},
        "insight_audit": plan.get("insight_audit") or su.get("insight_audit") or {},
        "insight_quality": plan.get("insight_quality") or su.get("insight_quality") or {},
        "structured_insights": plan.get("structured_insights") or su.get("structured_insights") or [],
        "primary_insight": plan.get("primary_insight") or su.get("primary_insight"),
    }


def _is_causal_insight(text: str) -> bool:
    low = text.lower()
    markers = (
        "главный фактор",
        "из‑за",
        "из-за",
        "микса sku",
        "драйвер",
        "компенсировали",
        "просадкой прибыли",
        "п.п.",
        "эффект",
        "риск концентрации",
        "убыточ",
        "норма",
        "превышает",
        "лидер",
    )
    return any(m in low for m in markers)


def _is_structured_insight_block(text: str) -> bool:
    low = text.lower()
    return "что произошло:" in low and ("почему:" in low or "действие:" in low)


def _is_data_quality_warning(text: str, snap: dict) -> bool:
    low = text.lower()
    markers = (
        "себестоимость",
        "cost coverage",
        "качеств",
        "data quality",
        "загрузите",
        "импортируйте",
        "не указана",
        "не согласуется",
        "устраните проблему данных",
    )
    if any(m in low for m in markers):
        return True
    cov = snap.get("cost_coverage_pct")
    if cov is not None:
        try:
            if Decimal(str(cov)) < Decimal("80") and "cost" in low:
                return True
        except Exception:
            pass
    return False


def _is_false_positive(text: str, snap: dict) -> bool:
    low = text.lower()
    if "insufficient_data" in low or "no governed anomalies" in low:
        return True
    if "catalog breadth" in low and "supports distributed" in low:
        return True
    margin = snap.get("margin")
    if margin is not None:
        try:
            m = Decimal(str(margin))
            if m > Decimal("20") and "margin" in low and "below" in low:
                return True
        except Exception:
            pass
    return False
