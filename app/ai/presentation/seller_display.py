"""Seller-facing presentation helpers — localization and internal-field stripping."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from app.dto.domain_analyst_dto import DomainFindingDTO

_DOMAIN_LABELS_RU: dict[str, str] = {
    "sales_analyst": "Продажи",
    "ads_analyst": "Реклама",
    "funnel_analyst": "Ассортимент",
    "inventory_analyst": "Склад и остатки",
    "marketplace_comparison_analyst": "Сравнение площадок",
    "anomaly_analyst": "Качество данных",
    "logistics_analyst": "Логистика",
    "returns_analyst": "Возвраты",
    "revenue_change_analyst": "Выручка",
    "concentration_analyst": "Концентрация SKU",
}

_ANALYST_LABEL_EN: dict[str, str] = {
    "Sales Analyst": "Продажи",
    "Ads Analyst": "Реклама",
    "Funnel Analyst": "Ассортимент",
    "Inventory Analyst": "Склад и остатки",
    "Marketplace Comparison Analyst": "Сравнение площадок",
    "Anomaly Analyst": "Качество данных",
    "Logistics Analyst": "Логистика",
    "Returns Analyst": "Возвраты",
    "Revenue Change Analyst": "Выручка",
    "Concentration Analyst": "Концентрация SKU",
}

_PRIORITY_TIER_RU: dict[str, str] = {
    "today": "Сделать сегодня",
    "this_week": "На этой неделе",
    "informational": "Информация",
    "high": "Высокий",
    "medium": "Средний",
    "low": "Низкий",
}

_RISK_RU: dict[str, str] = {
    "low": "Низкий",
    "medium": "Средний",
    "high": "Высокий",
    "critical": "Критический",
}

_WORKFLOW_STATE_RU: dict[str, str] = {
    "active": "Активна",
    "saved": "В избранном",
    "snoozed": "Отложена",
    "completed": "Выполнена",
    "dismissed": "Скрыта",
    "waiting_for_data": "Жду данные",
    "done_today": "На сегодня",
}


def _looks_russian(text: str) -> bool:
    return any("\u0400" <= c <= "\u04FF" for c in text)


def confidence_label_ru(value: float | str | None) -> str:
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "—"
    if v >= 0.85:
        return "Высокая"
    if v >= 0.65:
        return "Средняя"
    return "Низкая"


def risk_label_ru(value: str | None) -> str:
    if not value:
        return "—"
    return _RISK_RU.get(str(value).lower(), str(value))


def priority_tier_label_ru(value: str | None) -> str:
    if not value:
        return "—"
    return _PRIORITY_TIER_RU.get(str(value).lower(), str(value))


def workflow_state_label_ru(value: str | None) -> str:
    if not value:
        return "—"
    return _WORKFLOW_STATE_RU.get(str(value).lower(), str(value))


def seller_domain_label(analyst_id: str | None, analyst_label: str | None = None) -> str:
    if analyst_id and analyst_id in _DOMAIN_LABELS_RU:
        return _DOMAIN_LABELS_RU[analyst_id]
    if analyst_label and analyst_label in _ANALYST_LABEL_EN:
        return _ANALYST_LABEL_EN[analyst_label]
    if analyst_label and _looks_russian(analyst_label):
        return analyst_label
    if analyst_id:
        return analyst_id.replace("_analyst", "").replace("_", " ").title()
    return "Сигнал по данным"


def seller_what_happened(finding: DomainFindingDTO) -> str:
    """Prefer Russian copy; fall back to recommended action text, then finding_id template."""
    stmt = finding.statement.strip()
    if _looks_russian(stmt):
        return stmt
    for action in finding.recommended_actions:
        action_text = str(action).strip()
        if _looks_russian(action_text):
            return action_text
    return _statement_fallback_ru(finding.finding_id, stmt)


def seller_why_text(*, finding_id: str | None, why: str) -> str:
    """Strip internal English reasoning; keep Russian business rationale."""
    text = (why or "").strip()
    if not text:
        return "Сигнал основан на загруженных отчётах и KPI за выбранный период."
    if _is_internal_reasoning(text):
        return _why_fallback_ru(finding_id)
    if not _looks_russian(text):
        return _why_fallback_ru(finding_id)
    text = text.replace("mix SKU", "структуры SKU")
    text = text.replace("unit economics", "экономики единицы товара")
    text = text.replace("governed-метриками", "данными отчётов")
    text = text.replace("governed KPI snapshot and deterministic analysts", "KPI из загруженных отчётов")
    if "supporting signal" in text.lower():
        return _why_fallback_ru(finding_id)
    return text


def _is_internal_reasoning(text: str) -> bool:
    low = text.lower()
    markers = (
        "assigned severity",
        "analyst_confidence",
        "confidence propagation",
        "multi-layer",
        "multi layer",
        "warehouse_stock_snapshots",
        "deterministic analysts",
        "rank=1 confidence",
    )
    return any(m in low for m in markers)


def _why_fallback_ru(finding_id: str | None) -> str:
    fid = finding_id or ""
    mapping = {
        "revenue_drop": "Изменение объёма продаж и структуры SKU относительно сравниваемого периода.",
        "revenue_growth": "Рост выручки связан с изменением объёма или структуры SKU.",
        "profit_drop": "Прибыль снизилась из-за структуры SKU, расходов маркетплейса или себестоимости.",
        "logistics_high_share": "Логистика занимает непропорционально высокую долю выручки.",
        "logistics_share_growth": "Рост логистики ухудшает экономику продаж без роста цены.",
        "returns_high_rate": "Возвраты съедают маржу и могут указывать на проблемы карточки или качества.",
        "inventory_dead_stock": "SKU без продаж блокируют оборотный капитал и занимают склад.",
    }
    for prefix, reason in mapping.items():
        if fid.startswith(prefix):
            return reason
    return "Сигнал основан на загруженных отчётах и KPI за выбранный период."


def _statement_fallback_ru(finding_id: str, english_statement: str) -> str:
    fid = finding_id or ""
    if fid.startswith("logistics_high_share"):
        m = re.search(r"([\d.]+)%", english_statement)
        pct = m.group(1) if m else "—"
        return f"Доля логистики в выручке — {pct}%, выше рекомендуемого порога."
    if fid.startswith("logistics_share_growth"):
        m = re.search(r"([\d.]+)", english_statement)
        delta = m.group(1) if m else "—"
        return f"Доля логистики выросла на {delta} п.п. относительно сравниваемого периода."
    if fid.startswith("returns_high_rate"):
        m = re.search(r"([\d.]+)%", english_statement)
        rate = m.group(1) if m else "—"
        return f"Уровень возвратов — {rate}%, выше допустимого порога."
    if fid.startswith("revenue_drop"):
        m = re.search(r"([\d.]+)%", english_statement)
        pct = m.group(1) if m else "—"
        return f"Выручка снизилась на {pct}% относительно сравниваемого периода."
    if fid.startswith("revenue_growth"):
        m = re.search(r"([\d.]+)%", english_statement)
        pct = m.group(1) if m else "—"
        return f"Выручка выросла на {pct}% относительно сравниваемого периода."
    if fid.startswith("concentration"):
        m = re.search(r"([\d.]+)%", english_statement)
        pct = m.group(1) if m else "—"
        return f"Концентрация выручки на топ-SKU — {pct}%."
    if _looks_russian(english_statement):
        return english_statement
    return "Обнаружен значимый сигнал по данным периода — см. рекомендуемое действие."


def sanitize_domain_insight_for_seller(insight: dict[str, Any]) -> dict[str, Any]:
    """Strip internal analyst fields; expose only seller-safe Russian copy."""
    analyst_id = str(insight.get("analyst_id") or "")
    finding_id = str(insight.get("insight_id") or "").split(":")[-1]
    statement = str(insight.get("statement") or "").strip()
    actions = insight.get("recommended_actions") or []

    fake = DomainFindingDTO(
        finding_id=finding_id,
        statement=statement,
        confidence=_as_decimal(insight.get("confidence"), default=Decimal("0.5")),
        severity=str(insight.get("severity") or "medium"),
        evidence_refs=list(insight.get("evidence_refs") or []),
        recommended_actions=[str(a) for a in actions],
    )
    what = seller_what_happened(fake)
    why_raw = str(insight.get("reasoning_summary") or "")
    why = seller_why_text(finding_id=finding_id, why=why_raw if not _is_internal_reasoning(why_raw) else "")

    payload: dict[str, Any] = {
        "insight_id": insight.get("insight_id"),
        "domain": seller_domain_label(analyst_id, insight.get("analyst_label")),
        "statement": what,
        "recommended_actions": [str(a) for a in actions if _looks_russian(str(a))][:3],
        "priority_rank": insight.get("priority_rank"),
    }
    if why and why != what:
        payload["why_it_matters"] = why
    return payload


def sanitize_domain_insights_for_seller(insights: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [sanitize_domain_insight_for_seller(i) for i in insights]


def sanitize_evidence_graph_for_seller(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = []
    for raw in graph.get("nodes") or []:
        if not isinstance(raw, dict):
            continue
        label = str(raw.get("label") or "Доказательство")
        for en, ru in _ANALYST_LABEL_EN.items():
            if label.startswith(f"{en}:"):
                rest = label.split(":", 1)[-1].strip()
                domain = ru
                fake = DomainFindingDTO(
                    finding_id="evidence",
                    statement=rest,
                    confidence=_as_decimal(None, default=Decimal("0.5")),
                    severity="medium",
                    evidence_refs=[],
                    recommended_actions=[rest] if _looks_russian(rest) else [],
                )
                label = f"{domain}: {seller_what_happened(fake)}"
                break
        source_type = str(raw.get("source_type") or "")
        if source_type == "domain_analyst":
            source_type = "данные отчёта"
        nodes.append({**raw, "label": label, "source_type": source_type})
    return {**graph, "nodes": nodes}


def sanitize_reasoning_trace_for_seller(trace: dict[str, Any]) -> dict[str, Any]:
    """Return seller-safe trace: domain insights sanitized, no raw multi-layer dump."""
    out = dict(trace)
    insights = out.get("domain_insights")
    if isinstance(insights, list):
        out["domain_insights"] = sanitize_domain_insights_for_seller(insights)
    out.pop("multi_layer", None)
    out.pop("agent_messages", None)
    steps = out.get("steps")
    if isinstance(steps, list):
        out["steps"] = []
    return out


def format_confidence_explanation_ru(confidence: float | None, *, flags: list[str] | None = None) -> str:
    label = confidence_label_ru(confidence)
    parts = [f"Уверенность в рекомендации: {label}."]
    if flags:
        from app.ai.product.seller_usefulness import _flag_label

        parts.append(f"Учтено: {', '.join(_flag_label(f) for f in flags)}.")
    return " ".join(parts)


def _as_decimal(value: object, *, default: Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        return default
    try:
        return Decimal(str(value))
    except Exception:
        return default
