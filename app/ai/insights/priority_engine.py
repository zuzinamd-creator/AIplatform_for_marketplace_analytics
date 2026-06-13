"""Insight Priority Engine — rank governed findings for seller-facing output."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.ai.insights.quality import compute_insight_quality_score
from app.dto.domain_analyst_dto import DomainAnalystOutputDTO, DomainFindingDTO, ExecutiveInsightDTO


@dataclass(frozen=True)
class StructuredInsight:
    insight_id: str
    priority_level: int
    what_happened: str
    why: str
    confidence: float
    recommended_action: str
    source: str
    finding_id: str | None = None

    def format_block(self) -> str:
        conf_label = _confidence_label(self.confidence)
        return (
            f"Что произошло:\n{self.what_happened}\n\n"
            f"Почему:\n{self.why}\n\n"
            f"Уверенность:\n{conf_label} ({self.confidence:.2f}).\n\n"
            f"Действие:\n{self.recommended_action}"
        )

    def headline(self) -> str:
        line = self.what_happened.strip().split("\n")[0]
        return line[:255]

    def domain(self) -> str:
        return _insight_domain(self)


# Core business domains — always eligible for L1
_CORE_L1_PREFIXES = (
    "revenue_drop",
    "revenue_growth",
    "profit_drop",
    "revenue_sku_driver",
    "concentration_top",
    "returns_high_rate",
    "returns_rate_growth",
    "returns_sku_leader",
    "logistics_high_share",
    "logistics_share_growth",
    "logistics_sku_anomaly",
    "sales_low_margin",
)

_L3_FINDING_PREFIXES = (
    "sales_revenue_present",
    "funnel_breadth_ok",
    "mp_context",
    "ads_no_governed_spend",
    "inventory_limited_signals",
    "inventory_healthy",
    "anomaly_none",
)

# Causal markers for deep period insights (non-inventory)
_DEEP_L1_MARKERS = (
    "убыточ",
    "высокая логистика",
    "высокая комиссия",
    "низкая маржа",
    "концентрац",
    "упала на",
    "выросла на",
    "главный фактор",
    "драйвер",
)

_INVENTORY_DEEP_MARKERS = (
    "заморож",
    "остатк",
    "мёртв",
    "мертв",
    "медленн",
    "складск",
    "неликвид",
    "оборачиваем",
)

_REVENUE_PROTECTION_DOMAINS = frozenset({"revenue", "profit", "margin", "logistics", "returns", "concentration"})

_EXECUTIVE_DOMAIN_ORDER = (
    "revenue",
    "profit",
    "margin",
    "logistics",
    "returns",
    "concentration",
    "inventory",
    "other",
)


def priority_level_for_finding(finding_id: str, severity: str) -> int:
    """Assign priority level with inventory escalation rules (Phase 6.3.0B)."""
    fid = finding_id.lower()

    if fid in _L3_FINDING_PREFIXES or any(fid.startswith(p) for p in _L3_FINDING_PREFIXES):
        return 3

    if fid == "sales_top_sku":
        return 1

    if any(fid.startswith(p) for p in _CORE_L1_PREFIXES):
        return 1

    if fid.startswith("inventory_"):
        if _inventory_escalates_to_l1(fid, severity):
            return 1
        return 2

    if severity in ("high", "critical"):
        return 2
    return 2


def _inventory_escalates_to_l1(finding_id: str, severity: str) -> bool:
    """Inventory becomes L1 only in critical scenarios."""
    fid = finding_id.lower()
    if fid == "inventory_dead_stock" and severity in ("high", "critical"):
        return True
    if fid == "inventory_frozen_capital" and severity == "high":
        return True
    return False


def priority_level_for_text(text: str) -> int:
    low = text.lower()
    if any(m in low for m in _INVENTORY_DEEP_MARKERS):
        if "мёртв" in low or "мертв" in low:
            return 1
        return 2
    if any(m in low for m in _DEEP_L1_MARKERS):
        return 1
    if "себестоимость не указана" in low or "cost coverage" in low:
        return 2
    if re.search(r"составил[аи]?\s+\d", low):
        return 3
    return 2


def structured_from_finding(
    *,
    finding: DomainFindingDTO,
    analyst_id: str,
    source: str = "domain_analyst",
) -> StructuredInsight:
    level = priority_level_for_finding(finding.finding_id, finding.severity)
    action = finding.recommended_actions[0] if finding.recommended_actions else "Сверьте KPI на Dashboard и выберите действие по SKU."
    why = _why_from_finding(finding)
    return StructuredInsight(
        insight_id=f"{analyst_id}:{finding.finding_id}",
        priority_level=level,
        what_happened=finding.statement.strip(),
        why=why,
        confidence=float(finding.confidence),
        recommended_action=action.strip(),
        source=source,
        finding_id=finding.finding_id,
    )


def structured_from_executive(ins: ExecutiveInsightDTO) -> StructuredInsight:
    fid = ins.insight_id.split(":")[-1] if ":" in ins.insight_id else ins.insight_id
    fake = DomainFindingDTO(
        finding_id=fid,
        statement=ins.statement,
        confidence=ins.confidence,
        severity=ins.severity,
        evidence_refs=ins.evidence_refs,
        recommended_actions=ins.recommended_actions or ["Сверьте детали в карточке рекомендации."],
    )
    out = structured_from_finding(
        finding=fake,
        analyst_id=ins.analyst_id,
        source="executive_insight",
    )
    return StructuredInsight(
        insight_id=ins.insight_id,
        priority_level=out.priority_level,
        what_happened=out.what_happened,
        why=ins.reasoning_summary or out.why,
        confidence=float(ins.confidence),
        recommended_action=out.recommended_action,
        source="executive_insight",
        finding_id=fid,
    )


def structured_from_deep_bullet(text: str, *, index: int) -> StructuredInsight:
    level = priority_level_for_text(text)
    action = _action_from_deep(text)
    why = _why_from_deep(text)
    what = text.strip().split("—")[0].split(" - ")[0].strip()
    if not what:
        what = text.strip()[:200]
    fid = None
    low = text.lower()
    if any(m in low for m in _INVENTORY_DEEP_MARKERS):
        if "мёртв" in low or "мертв" in low:
            fid = "inventory_dead_stock"
        elif "концентрац" in low:
            fid = "inventory_stock_concentration"
        elif "медлен" in low:
            fid = "inventory_slow_movers"
        else:
            fid = "inventory_frozen_capital"
    return StructuredInsight(
        insight_id=f"deep:{index}",
        priority_level=level,
        what_happened=what,
        why=why,
        confidence=0.82 if level == 1 else 0.72,
        recommended_action=action,
        source="deep_period_insights",
        finding_id=fid,
    )


def structured_from_headline(headline: str) -> StructuredInsight | None:
    if not headline or not headline.strip():
        return None
    if priority_level_for_text(headline) >= 3 and "сравнение периодов" not in headline.lower():
        return None
    level = 1 if _has_causal_headline(headline) else 2
    return StructuredInsight(
        insight_id="causal_headline",
        priority_level=level,
        what_happened=headline.strip(),
        why="Сравнение governed-периодов и структуры продаж по SKU.",
        confidence=0.88 if level == 1 else 0.75,
        recommended_action="Проверьте SKU-драйверы периода и при необходимости скорректируйте цену, остатки или продвижение.",
        source="causal_headline",
        finding_id="revenue_period_driver",
    )


def collect_structured_insights(
    *,
    domain_outputs: list[DomainAnalystOutputDTO] | None,
    executive_insights: list[ExecutiveInsightDTO] | None,
    deep_bullets: list[str] | None,
    causal_headline: str | None,
) -> list[StructuredInsight]:
    seen: set[str] = set()
    items: list[StructuredInsight] = []

    def add(item: StructuredInsight) -> None:
        key = _normalize_key(item.what_happened)
        if key in seen:
            return
        seen.add(key)
        items.append(item)

    if causal_headline:
        head = structured_from_headline(causal_headline)
        if head:
            add(head)

    analyst_inventory_fids: set[str] = set()
    if domain_outputs:
        for out in domain_outputs:
            if out.analyst_id.value == "inventory_analyst":
                for f in out.findings:
                    analyst_inventory_fids.add(f.finding_id)

    for idx, bullet in enumerate(deep_bullets or []):
        if not bullet or not bullet.strip():
            continue
        deep_item = structured_from_deep_bullet(str(bullet), index=idx)
        if _is_inventory_insight(deep_item) and _deep_bullet_redundant(deep_item, analyst_inventory_fids):
            continue
        add(deep_item)

    if executive_insights:
        for ins in executive_insights:
            add(structured_from_executive(ins))

    if domain_outputs:
        for out in domain_outputs:
            for finding in out.findings:
                if finding.finding_id in _L3_FINDING_PREFIXES:
                    continue
                item = structured_from_finding(finding=finding, analyst_id=out.analyst_id.value)
                if executive_insights and item.priority_level >= 3:
                    continue
                add(item)

    items = _dedupe_inventory_semantics(items)
    items.sort(key=lambda x: (x.priority_level, -x.confidence))
    return items


def pick_executive_lead(insights: list[StructuredInsight], *, max_items: int = 3) -> list[StructuredInsight]:
    """Revenue-protected, domain-balanced executive lead (Phase 6.3.0B)."""
    if not insights:
        return []
    candidates = sorted(insights, key=lambda x: (x.priority_level, -_estimated_quality(x)))
    primary = _select_primary_insight(candidates)
    return _balanced_executive_lead(candidates, primary=primary, max_items=max_items)


def _select_primary_insight(candidates: list[StructuredInsight]) -> StructuredInsight:
    """Revenue protection: prefer revenue/profit unless inventory is escalated with higher IQ."""
    revenue_pool = [
        c
        for c in candidates
        if c.domain() in _REVENUE_PROTECTION_DOMAINS or c.finding_id == "sales_top_sku"
    ]
    inv_escalated = [
        c for c in candidates if _is_inventory_insight(c) and c.priority_level == 1
    ]
    if revenue_pool:
        best_revenue = max(revenue_pool, key=_estimated_quality)
        if inv_escalated:
            best_inv = max(inv_escalated, key=_estimated_quality)
            if _estimated_quality(best_inv) > _estimated_quality(best_revenue) + 8.0:
                return best_inv
        return best_revenue
    if inv_escalated:
        return max(inv_escalated, key=_estimated_quality)
    return candidates[0]


def _balanced_executive_lead(
    candidates: list[StructuredInsight],
    *,
    primary: StructuredInsight,
    max_items: int,
) -> list[StructuredInsight]:
    picked: list[StructuredInsight] = [primary]
    used_domains: set[str] = {primary.domain()}
    inv_slots = 1 if primary.domain() == "inventory" else 0

    for domain in _EXECUTIVE_DOMAIN_ORDER:
        if len(picked) >= max_items:
            break
        if domain in used_domains:
            continue
        pool = [c for c in candidates if c.domain() == domain and c.insight_id not in {p.insight_id for p in picked}]
        if not pool:
            continue
        if domain == "inventory":
            if inv_slots >= 1:
                continue
            best = max(pool, key=_estimated_quality)
            picked.append(best)
            inv_slots += 1
            used_domains.add(domain)
            continue
        best = max(pool, key=_estimated_quality)
        picked.append(best)
        used_domains.add(domain)

    if len(picked) < max_items:
        for c in candidates:
            if len(picked) >= max_items:
                break
            if c.insight_id in {p.insight_id for p in picked}:
                continue
            if _is_inventory_insight(c) and inv_slots >= 1:
                continue
            picked.append(c)
            if _is_inventory_insight(c):
                inv_slots += 1

    return picked[:max_items]


def _estimated_quality(item: StructuredInsight) -> float:
    return compute_insight_quality_score(
        what_happened=item.what_happened,
        why=item.why,
        action=item.recommended_action,
        confidence=item.confidence,
        priority_level=item.priority_level,
    ).overall


def _dedupe_inventory_semantics(items: list[StructuredInsight]) -> list[StructuredInsight]:
    """Keep strongest inventory insight per semantic bucket."""
    best_by_bucket: dict[str, StructuredInsight] = {}
    non_inv: list[StructuredInsight] = []
    for item in items:
        bucket = _inventory_semantic_bucket(item)
        if bucket is None:
            non_inv.append(item)
            continue
        prev = best_by_bucket.get(bucket)
        if prev is None or _estimated_quality(item) > _estimated_quality(prev):
            best_by_bucket[bucket] = item
    merged = non_inv + list(best_by_bucket.values())
    merged.sort(key=lambda x: (x.priority_level, -x.confidence))
    return merged


def _inventory_semantic_bucket(item: StructuredInsight) -> str | None:
    if not _is_inventory_insight(item):
        return None
    fid = (item.finding_id or "").lower()
    text = item.what_happened.lower()
    if "dead_stock" in fid or "мёртв" in text or "мертв" in text:
        return "inv:dead"
    if "slow" in fid or "медлен" in text:
        return "inv:slow"
    if "concentration" in fid or "концентрац" in text:
        return "inv:concentration"
    if "risk" in fid or "риск" in text:
        return "inv:risk"
    if "frozen" in fid or "заморож" in text:
        return "inv:frozen"
    return "inv:other"


def _deep_bullet_redundant(deep_item: StructuredInsight, analyst_fids: set[str]) -> bool:
    fid = deep_item.finding_id
    if not fid:
        return False
    if fid == "inventory_frozen_capital" and "inventory_frozen_capital" in analyst_fids:
        return True
    if fid == "inventory_stock_concentration" and (
        "inventory_stock_concentration" in analyst_fids or "inventory_risk_high" in analyst_fids
    ):
        return True
    if fid == "inventory_dead_stock" and "inventory_dead_stock" in analyst_fids:
        return True
    if fid == "inventory_slow_movers" and "inventory_slow_movers" in analyst_fids:
        return True
    return False


def _insight_domain(item: StructuredInsight) -> str:
    fid = (item.finding_id or "").lower()
    text = item.what_happened.lower()
    if fid == "sales_top_sku" or "leading sku" in text or fid.startswith("revenue_"):
        return "revenue"
    if fid.startswith("profit_") or "sales_low_margin" in fid or "маржа" in text or "убыточ" in text:
        return "profit" if "убыточ" in text or "profit" in fid else "margin"
    if fid.startswith("logistics_") or "логистик" in text:
        return "logistics"
    if fid.startswith("returns_") or "возврат" in text:
        return "returns"
    if fid.startswith("concentration_") or ("концентрац" in text and "остат" not in text):
        return "concentration"
    if _is_inventory_insight(item):
        return "inventory"
    if item.source == "causal_headline":
        return "revenue"
    return "other"


def _is_inventory_insight(item: StructuredInsight) -> bool:
    fid = item.finding_id or ""
    if fid.startswith("inventory_"):
        return True
    if "inventory_analyst" in item.insight_id:
        return True
    low = item.what_happened.lower()
    return any(m in low for m in _INVENTORY_DEEP_MARKERS)


def _why_from_finding(finding: DomainFindingDTO) -> str:
    fid = finding.finding_id
    mapping = {
        "revenue_drop": "Изменение объёма продаж и структуры SKU относительно сравниваемого периода.",
        "revenue_growth": "Рост выручки связан с изменением объёма или mix SKU, а не только с KPI-итогом.",
        "profit_drop": "Прибыль снизилась из-за mix SKU, расходов маркетплейса или себестоимости.",
        "sales_top_sku": "Лидер по выручке задаёт основной риск и потенциал роста периода — важнее общих KPI.",
        "concentration_top1_risk": "Высокая доля одного SKU повышает риск просадки выручки.",
        "concentration_top3_risk": "Концентрация на нескольких SKU ограничивает устойчивость продаж.",
        "returns_high_rate": "Возвраты съедают маржу и могут указывать на проблемы карточки или качества.",
        "returns_rate_growth": "Рост возвратов ухудшает чистую выручку периода.",
        "logistics_high_share": "Логистика занимает непропорционально высокую долю выручки.",
        "logistics_share_growth": "Рост логистики ухудшает unit economics без роста цены.",
        "sales_low_margin": "Маржа ниже безопасного порога при текущей себестоимости.",
        "inventory_dead_stock": "SKU без продаж блокируют оборотный капитал и занимают склад.",
        "inventory_slow_movers": "Низкая оборачиваемость сигнализирует о переизбытке или слабом спросе.",
        "inventory_frozen_capital": "Деньги заморожены в остатках — учитывайте как supporting signal, не замену выручки.",
        "inventory_stock_concentration": "Капитал в остатках сконцентрирован на нескольких SKU — риск неликвида.",
        "inventory_risk_high": "Комбинация складских сигналов повышает операционный риск.",
    }
    for prefix, reason in mapping.items():
        if fid.startswith(prefix):
            return reason
    if finding.evidence_refs:
        return f"Подтверждено governed-метриками: {', '.join(finding.evidence_refs[:3])}."
    return "Вывод основан на governed KPI snapshot и deterministic analysts."


def _why_from_deep(text: str) -> str:
    low = text.lower()
    if "убыточ" in low:
        return "Отрицательная unit economics по SKU снижает прибыль периода."
    if "логистик" in low:
        return "Доля логистики в выручке SKU выше нормы."
    if "комисс" in low:
        return "Комиссия WB на SKU давит на маржу."
    if "маржа" in low:
        return "Низкая маржа оставляет мало пространства для скидок и рекламы."
    if "себестоим" in low:
        return "Без себестоимости прибыль и маржа по SKU недостоверны."
    if any(m in low for m in _INVENTORY_DEEP_MARKERS):
        return "Складской сигнал дополняет картину периода, но не заменяет анализ выручки и маржи."
    return "Сигнал из deep period insights по governed данным."


def _action_from_deep(text: str) -> str:
    if "—" in text:
        tail = text.split("—", 1)[1].strip()
        if len(tail) >= 15:
            return tail.rstrip(".") + "."
    low = text.lower()
    if "убыточ" in low:
        return "Проверьте себестоимость, логистику и цену проблемного SKU."
    if "логистик" in low:
        return "Оцените упаковку, габариты и распределение остатков по SKU."
    if "остат" in low or "сток" in low or "оборачива" in low or "заморож" in low:
        return "Проведите ревизию остатков и скорректируйте закупки по проблемным SKU."
    if "комисс" in low:
        return "Проверьте категорию, акции и цену после СПП."
    if "себестоим" in low:
        return "Загрузите себестоимость для непокрытых SKU."
    return "Сверьте SKU в Dashboard и выберите корректирующее действие."


def _confidence_label(value: float) -> str:
    if value >= 0.85:
        return "Высокая"
    if value >= 0.65:
        return "Средняя"
    return "Низкая"


def _has_causal_headline(text: str) -> bool:
    low = text.lower()
    return any(
        m in low
        for m in ("главный фактор", "драйвер", "sku", "п.п.", "компенсировали", "упала", "выросла")
    )


def _normalize_key(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())[:160]
