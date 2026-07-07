"""Seller-facing presentation helpers — localization and internal-field stripping."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, cast

from app.dto.domain_analyst_dto import DomainFindingDTO, SeverityLevel

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


_SELLER_TERM_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("governed-периодов", "сравниваемых периодов"),
    ("governed-метриками", "данными отчётов"),
    ("governed KPI snapshot and deterministic analysts", "KPI из загруженных отчётов"),
    ("governed KPI", "KPI из отчётов"),
    ("governed данным", "загруженным отчётам"),
    ("governed метрики", "показатели из отчётов"),
    ("governed", "загруженных отчётов"),
    ("deep period insights", "анализа периода"),
    ("deep period", "анализа периода"),
    ("cost_history", "история себестоимости"),
    ("live-API маркететплейса", "данных из кабинета маркетплейса в реальном времени"),
    ("live-API", "кабинета маркетплейса"),
    ("live API", "кабинета маркетплейса"),
)


def sanitize_seller_text(text: str) -> str:
    """Replace internal/English terms with seller-facing Russian."""
    if not text:
        return text
    out = str(text)
    for old, new in _SELLER_TERM_REPLACEMENTS:
        out = out.replace(old, new)
    return out


def sanitize_action_plan_for_seller(plan: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(plan, dict):
        return {}
    out = dict(plan)
    for key in ("analysis_limitations", "advertising_warning", "recommended_action", "why_this_matters"):
        if key in out and out[key]:
            out[key] = sanitize_seller_text(str(out[key]))
    su = out.get("seller_usefulness")
    if isinstance(su, dict):
        su_out = dict(su)
        for key in (
            "why_this_matters",
            "concrete_next_action",
            "confidence_explanation",
            "analysis_limitations",
            "expected_business_impact",
            "executive_summary_v2_text",
            "what_to_do_today",
        ):
            if key in su_out and su_out[key]:
                su_out[key] = sanitize_seller_text(str(su_out[key]))
        limits = su_out.get("limitations")
        if isinstance(limits, list):
            su_out["limitations"] = [sanitize_seller_text(str(x)) for x in limits]
        out["seller_usefulness"] = su_out
    bc = out.get("business_coverage")
    if isinstance(bc, dict):
        bc_out = dict(bc)
        if bc_out.get("analysis_limitations"):
            bc_out["analysis_limitations"] = sanitize_seller_text(str(bc_out["analysis_limitations"]))
        if bc_out.get("advertising_warning"):
            bc_out["advertising_warning"] = sanitize_seller_text(str(bc_out["advertising_warning"]))
        out["business_coverage"] = bc_out
    pd = out.get("period_decision")
    if isinstance(pd, dict):
        pd_out = dict(pd)
        for key in ("action", "alternative_action", "data_request"):
            if pd_out.get(key):
                pd_out[key] = sanitize_seller_text(str(pd_out[key]))
        out["period_decision"] = pd_out
    cards = out.get("driver_cards")
    if isinstance(cards, list):
        out["driver_cards"] = [sanitize_driver_card_for_seller(c) for c in cards if isinstance(c, dict)]
    return out


def sanitize_driver_card_for_seller(card: dict[str, Any]) -> dict[str, Any]:
    out = dict(card)
    for key in ("cause", "action", "effect_label"):
        if out.get(key):
            out[key] = sanitize_seller_text(str(out[key]))
    checks = out.get("checks")
    if isinstance(checks, list):
        out["checks"] = [sanitize_seller_text(str(x)) for x in checks]
    return out


def sanitize_recommendation_for_seller(
    *,
    title: str,
    summary: str,
    action_plan: dict[str, Any] | None,
) -> tuple[str, str, dict[str, Any]]:
    plan = sanitize_action_plan_for_seller(action_plan)
    cleaned = strip_limitations_from_summary(sanitize_seller_text(summary), plan)
    fixed_summary = ensure_summary_action_separated(cleaned, plan)
    return (
        sanitize_seller_text(title),
        fixed_summary,
        plan,
    )


_DEFAULT_SELLER_ACTION = (
    "Сверьте KPI на Dashboard и выберите корректирующее действие по проблемным SKU."
)

_ACTION_VERB_STARTS = (
    "проверьте",
    "снизьте",
    "увеличьте",
    "пересмотрите",
    "загрузите",
    "оцените",
    "проведите",
    "сверьте",
    "рассмотрите",
    "импортируйте",
    "скорректируйте",
    "добавьте",
    "оптимизируйте",
    "остановите",
    "диверсифицируйте",
    "продвигайте",
)

_ANALYTICS_SENTENCE_STARTS = (
    "выручка",
    "прибыль",
    "маржа",
    "основной",
    "главный",
    "драйвер",
    "концентрация",
    "объём",
    "объем",
    "капитал",
    "sku ",
)


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
    """Russian narrative of the finding — never copy recommended_actions (often mixed with actions)."""
    stmt = finding.statement.strip()
    if _looks_russian(stmt) and not _text_is_action_heavy(stmt):
        return stmt
    base = _statement_fallback_ru(finding.finding_id, stmt)
    return _enrich_what_with_driver(base, finding)


def seller_action_from_finding(finding: DomainFindingDTO) -> str:
    """Seller-facing imperative actions only."""
    for raw in finding.recommended_actions:
        extracted = extract_seller_action_text(str(raw), finding_id=finding.finding_id)
        if extracted:
            return extracted
    return _action_fallback_ru(finding.finding_id)


def extract_seller_action_text(text: str, *, finding_id: str | None = None) -> str:
    """Pull imperative sentences from mixed analyst copy; return numbered list or empty."""
    if not text or not str(text).strip():
        return ""
    actions = _extract_imperative_sentences(str(text))
    sku = _extract_sku_reference(str(text))
    expanded: list[str] = []
    for sentence in actions:
        expanded.extend(_expand_combined_check_sentence(sentence, sku))
    if expanded:
        return _format_numbered_actions(expanded)
    if _text_is_action_heavy(str(text)) and not _text_is_analytics_heavy(str(text)):
        return _format_numbered_actions([str(text).strip().rstrip(".") + "."])
    return ""


def strip_limitations_from_summary(summary: str, action_plan: dict[str, Any]) -> str:
    """Remove limitations tail from summary when served via action_plan (single UI source)."""
    if not summary:
        return summary
    out = re.sub(r"\n\n### Ограничения анализа[\s\S]*$", "", summary).strip()
    su = action_plan.get("seller_usefulness") or {}
    ad = str(su.get("advertising_warning") or action_plan.get("advertising_warning") or "").strip()
    if ad and out.endswith(ad):
        out = out[: -len(ad)].rstrip()
    return out


def ensure_summary_action_separated(summary: str, action_plan: dict[str, Any] | None) -> str:
    """On API read: fix stored summaries where «Что делать» duplicates analytics."""
    if not summary:
        return summary
    plan = action_plan or {}
    su = plan.get("seller_usefulness") or {}
    fid = None
    primary = plan.get("primary_insight") or {}
    if isinstance(primary, dict):
        fid = primary.get("finding_id")

    pd = plan.get("period_decision")
    period_action = None
    if isinstance(pd, dict) and pd.get("action"):
        period_action = extract_seller_action_text(str(pd["action"]), finding_id=fid) or str(
            pd["action"]
        )

    def _resolve_action() -> str:
        if period_action:
            return period_action
        for candidate in (su.get("concrete_next_action"), plan.get("recommended_action")):
            extracted = extract_seller_action_text(str(candidate or ""), finding_id=fid)
            if extracted:
                return extracted
        for label in ("Действие", "Что делать"):
            m = re.search(rf"{label}:\n(.*?)(?:\n\n(?:Почему|Уверенность|---|\Z))", summary, re.S)
            if m:
                extracted = extract_seller_action_text(m.group(1).strip(), finding_id=fid)
                if extracted:
                    return extracted
        return _action_fallback_ru(str(fid or ""))

    if "Что делать:" in summary:
        m_what = re.search(r"Что произошло:\n(.*?)\n\nЧто делать:", summary, re.S)
        m_act = re.search(r"Что делать:\n(.*?)(?:\n\nПочему это важно:|\Z)", summary, re.S)
        if m_what and m_act:
            what, act = m_what.group(1).strip(), m_act.group(1).strip()
            dash_fallback = bool(re.search(r"(?i)dashboard", act))
            if what == act or _text_is_analytics_heavy(act) or dash_fallback:
                new_act = _resolve_action()
                if new_act != act:
                    return summary.replace(f"Что делать:\n{act}", f"Что делать:\n{new_act}", 1)
        return summary

    if "Действие:" in summary and "Что делать:" not in summary:
        m_act = re.search(r"Действие:\n(.*?)(?:\n\n(?:---|Что произошло:)|\Z)", summary, re.S)
        if m_act:
            act = m_act.group(1).strip()
            new_act = _resolve_action()
            if new_act and new_act != act:
                return summary.replace(f"Действие:\n{act}", f"Действие:\n{new_act}", 1)
    return summary


def _text_is_action_heavy(text: str) -> bool:
    low = text.lower()
    return any(v in low for v in _ACTION_VERB_STARTS)


def _text_is_analytics_heavy(text: str) -> bool:
    low = text.lower().strip()
    if any(low.startswith(m) for m in _ANALYTICS_SENTENCE_STARTS):
        return True
    if re.search(r"[+-]?\d[\d\s]*%", low) and not _text_is_action_heavy(text):
        return True
    return False


def _extract_imperative_sentences(text: str) -> list[str]:
    found: list[str] = []
    for match in re.finditer(
        r"(?i)\b((?:проверьте|снизьте|увеличьте|пересмотрите|загрузите|оцените|проведите|"
        r"сверьте|рассмотрите|импортируйте|скорректируйте|добавьте|оптимизируйте|остановите|"
        r"диверсифицируйте|продвигайте)[^.!?]*[.!?])",
        text,
    ):
        sentence = match.group(1).strip()
        if sentence and sentence not in found:
            found.append(sentence if sentence.endswith(".") else sentence + ".")
    return found


def _extract_sku_reference(text: str) -> str | None:
    m = re.search(r"SKU\s+([^\s,.;]+)", text, re.I)
    return m.group(1) if m else None


def _expand_combined_check_sentence(sentence: str, sku: str | None) -> list[str]:
    low = sentence.lower()
    if "наличие" in low and "цен" in low and "реклам" in low:
        suffix = f" SKU {sku}." if sku else "."
        return [
            f"Проверьте остатки{suffix}",
            f"Проверьте цену относительно конкурентов{suffix}",
            f"Проверьте рекламную активность товара{suffix}",
        ]
    return [sentence]


def _format_numbered_actions(actions: list[str]) -> str:
    cleaned = [a.strip().rstrip(".") + "." for a in actions if a.strip()]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    return "\n".join(f"{i + 1}. {a}" for i, a in enumerate(cleaned))


def _enrich_what_with_driver(base: str, finding: DomainFindingDTO) -> str:
    raw = " ".join(str(a) for a in finding.recommended_actions)
    sku = _extract_sku_reference(raw)
    if not sku:
        return base
    fid = (finding.finding_id or "").lower()
    amt_m = re.search(r"\(([+-]?\d[\d\s]*)\s*₽\)", raw)
    if fid.startswith("revenue_drop") or "упала" in raw.lower():
        extra = f" Наибольший вклад в снижение внёс SKU {sku}"
        if amt_m:
            extra += f" ({amt_m.group(1).strip()} ₽)."
        else:
            extra += "."
        return base.rstrip(".") + "." + extra
    if fid.startswith("revenue_growth") or "выросла" in raw.lower():
        extra = f" Основной драйвер роста — SKU {sku}"
        if amt_m:
            extra += f" ({amt_m.group(1).strip()} ₽)."
        else:
            extra += "."
        return base.rstrip(".") + "." + extra
    return base


def _action_fallback_ru(finding_id: str | None) -> str:
    fid = (finding_id or "").lower()
    mapping = {
        "revenue_drop": (
            "1. Сверьте остатки и цены по топ-SKU периода.\n"
            "2. Проверьте рекламную активность по позициям с просадкой.\n"
            "3. Оцените влияние скидок и акций на выручку."
        ),
        "revenue_growth": (
            "1. Закрепите рост: проверьте остатки лидеров продаж.\n"
            "2. Пересмотрите цену и продвижение топ-SKU периода."
        ),
        "profit_drop": (
            "1. Проверьте себестоимость и комиссию по SKU с падением маржи.\n"
            "2. Оцените логистику и скидки по проблемным позициям."
        ),
        "logistics_high_share": "1. Проверьте габариты, упаковку и тарифы логистики WB по проблемным SKU.",
        "returns_high_rate": "1. Проверьте карточку, качество и комплектацию по SKU с высокими возвратами.",
        "inventory_dead_stock": "1. Снизьте остатки и пересмотрите цену SKU без продаж.",
        "inventory_slow_movers": "1. Снизьте закупку и проверьте видимость карточки проблемных SKU.",
    }
    for prefix, action in mapping.items():
        if fid.startswith(prefix):
            return action
    return _DEFAULT_SELLER_ACTION


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
        severity=cast(SeverityLevel, str(insight.get("severity") or "medium")),
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
        "recommended_actions": [
            a
            for a in (
                extract_seller_action_text(str(x), finding_id=finding_id) for x in actions
            )
            if a
        ][:3],
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
