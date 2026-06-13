"""Business Coverage Engine — which business blocks are available for AI analysis."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CoverageBlock:
    block_id: str
    label: str
    weight: int
    available: bool
    sub_items: tuple[tuple[str, bool], ...]


@dataclass(frozen=True)
class BusinessCoverageReport:
    blocks: tuple[CoverageBlock, ...]
    business_coverage_score: float
    missing_data_score: float
    included_in_analysis: tuple[str, ...]
    excluded_from_analysis: tuple[str, ...]
    coverage_formula: str
    advertising_data_coverage: bool
    advertising_warning: str | None
    analysis_limitations: str
    executive_summary_v2: dict
    root_cause_confidence: tuple[dict, ...]
    upload_priorities: tuple[str, ...]
    seller_usefulness_score: float


_UPLOAD_PRIORITY = (
    "Реклама маркетплейса (WB/Ozon)",
    "Себестоимость по SKU",
    "Налоги (УСН, НДС, взносы)",
    "Операционные расходы (ФОТ, аренда, подрядчики)",
    "Остатки и закупки",
)

_AD_WARNING = (
    "Данные по продвижению не загружены.\n\n"
    "AI не может определить:\n"
    "• влияние рекламы на рост продаж;\n"
    "• эффективность рекламных кампаний;\n"
    "• долю рекламного трафика;\n"
    "• окупаемость продвижения.\n\n"
    "Добавление рекламных данных повысит точность анализа."
)


def assess_business_coverage(
    snap: dict,
    *,
    deep_insights: list[str] | None = None,
    causal_headline: str | None = None,
) -> BusinessCoverageReport:
    """Evaluate governed data coverage and build seller-facing completeness payload."""
    deep = list(deep_insights or snap.get("deep_insights") or [])
    headline = causal_headline or snap.get("causal_headline")

    blocks = (
        _sales_block(snap),
        _marketplace_costs_block(snap),
        _cogs_block(snap),
        _promotion_block(snap),
        _external_marketing_block(snap),
        _tax_block(snap),
        _operational_block(snap),
        _financial_block(snap),
        _inventory_block(snap),
    )
    total_weight = sum(b.weight for b in blocks)
    covered_weight = sum(b.weight for b in blocks if b.available)
    score = round(covered_weight / total_weight * 100, 1) if total_weight else 0.0
    missing = round(100.0 - score, 1)

    included = _included_labels(blocks)
    excluded = _excluded_labels(blocks)
    formula = (
        f"Business Coverage = Σ(weight блоков с данными) / Σ(all weights) × 100% "
        f"= {covered_weight}/{total_weight} × 100% = {score:.1f}%"
    )

    ad_available = bool(snap.get("ad_spend_available"))
    ad_warning = None if ad_available else _AD_WARNING

    root_causes = _root_cause_confidence(snap, deep, headline, ad_available)
    upload = _upload_priorities(blocks, snap)
    exec_v2 = _executive_summary_v2(blocks, root_causes, upload)
    limitations = _analysis_limitations(included, excluded)
    usefulness = _seller_usefulness_score(score, snap, root_causes)

    return BusinessCoverageReport(
        blocks=blocks,
        business_coverage_score=score,
        missing_data_score=missing,
        included_in_analysis=included,
        excluded_from_analysis=excluded,
        coverage_formula=formula,
        advertising_data_coverage=ad_available,
        advertising_warning=ad_warning,
        analysis_limitations=limitations,
        executive_summary_v2=exec_v2,
        root_cause_confidence=root_causes,
        upload_priorities=upload,
        seller_usefulness_score=usefulness,
    )


def coverage_to_dict(report: BusinessCoverageReport) -> dict:
    return {
        "business_coverage_score": report.business_coverage_score,
        "missing_data_score": report.missing_data_score,
        "coverage_formula": report.coverage_formula,
        "blocks": [
            {
                "block_id": b.block_id,
                "label": b.label,
                "available": b.available,
                "weight": b.weight,
                "sub_items": [{"name": n, "available": a} for n, a in b.sub_items],
            }
            for b in report.blocks
        ],
        "included_in_analysis": list(report.included_in_analysis),
        "excluded_from_analysis": list(report.excluded_from_analysis),
        "advertising_data_coverage": report.advertising_data_coverage,
        "advertising_warning": report.advertising_warning,
        "analysis_limitations": report.analysis_limitations,
        "executive_summary_v2": report.executive_summary_v2,
        "root_cause_confidence": list(report.root_cause_confidence),
        "upload_priorities": list(report.upload_priorities),
        "seller_usefulness_score": report.seller_usefulness_score,
    }


def format_executive_summary_v2_text(report: BusinessCoverageReport) -> str:
    v2 = report.executive_summary_v2
    lines = ["### Что мы знаем точно"]
    lines.extend(f"• {x}" for x in v2.get("what_we_know") or ["—"])
    lines.append("")
    lines.append("### Что мы не можем оценить")
    lines.extend(f"• {x}" for x in v2.get("what_we_cannot_assess") or ["—"])
    lines.append("")
    lines.append("### Что желательно загрузить")
    lines.extend(f"{i + 1}. {x}" for i, x in enumerate(v2.get("recommended_uploads") or []))
    return "\n".join(lines)


def _dec(val: object) -> Decimal | None:
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except Exception:
        return None


def _has_positive(val: object) -> bool:
    d = _dec(val)
    return d is not None and d > 0


def _sales_block(snap: dict) -> CoverageBlock:
    rev = _has_positive(snap.get("total_revenue"))
    units = int(snap.get("sku_count") or 0) > 0 or _has_positive(snap.get("units_sold"))
    avg_check = snap.get("average_check") is not None
    returns = snap.get("return_rate_pct") is not None or _has_positive(snap.get("returns_amount"))
    subs = (
        ("выручка", rev),
        ("продажи (шт)", units),
        ("средний чек", avg_check),
        ("возвраты", returns),
    )
    return CoverageBlock("sales", "Продажи", 12, rev and (units or returns), subs)


def _marketplace_costs_block(snap: dict) -> CoverageBlock:
    subs = (
        ("комиссия", snap.get("commission_share_pct") is not None),
        ("логистика", snap.get("logistics_share_pct") is not None),
        ("хранение", snap.get("storage_share_pct") is not None),
        ("удержания", _has_positive(snap.get("deductions_total"))),
        ("штрафы", _has_positive(snap.get("penalties_total"))),
    )
    return CoverageBlock("marketplace_costs", "Расходы маркетплейса", 14, any(v for _, v in subs), subs)


def _cogs_block(snap: dict) -> CoverageBlock:
    cov = _dec(snap.get("cost_coverage_pct"))
    profit = _has_positive(snap.get("total_profit"))
    margin = snap.get("margin") is not None
    roi = snap.get("roi") is not None
    cost_hist = cov is not None and cov > 0
    subs = (
        ("cost_history", cost_hist),
        ("прибыль", profit),
        ("маржа", margin and (cov or Decimal("0")) >= Decimal("100")),
        ("ROI", roi),
    )
    return CoverageBlock("cogs", "Себестоимость и маржа", 14, cost_hist or profit, subs)


def _promotion_block(snap: dict) -> CoverageBlock:
    ad = bool(snap.get("ad_spend_available"))
    subs = (
        ("реклама WB/Ozon", ad),
        ("CTR", False),
        ("CPC", False),
        ("ACOS/ДРР", False),
        ("ROMI", False),
    )
    return CoverageBlock("marketplace_promotion", "Продвижение на маркетплейсе", 12, ad, subs)


def _external_marketing_block(snap: dict) -> CoverageBlock:
    subs = (
        ("Яндекс Директ", bool(snap.get("external_yandex_available"))),
        ("VK", bool(snap.get("external_vk_available"))),
        ("Telegram", bool(snap.get("external_telegram_available"))),
        ("блогеры", bool(snap.get("external_bloggers_available"))),
        ("SEO", bool(snap.get("external_seo_available"))),
    )
    return CoverageBlock("external_marketing", "Внешний маркетинг", 10, any(v for _, v in subs), subs)


def _tax_block(snap: dict) -> CoverageBlock:
    subs = (
        ("УСН", bool(snap.get("tax_usn_available"))),
        ("НДС", bool(snap.get("tax_vat_available"))),
        ("страховые взносы", bool(snap.get("tax_insurance_available"))),
        ("патент", bool(snap.get("tax_patent_available"))),
    )
    return CoverageBlock("tax", "Налоговая нагрузка", 10, any(v for _, v in subs), subs)


def _operational_block(snap: dict) -> CoverageBlock:
    subs = (
        ("зарплаты", bool(snap.get("opex_payroll_available"))),
        ("подрядчики", bool(snap.get("opex_contractors_available"))),
        ("контент", bool(snap.get("opex_content_available"))),
        ("упаковка", bool(snap.get("opex_packaging_available"))),
        ("аренда", bool(snap.get("opex_rent_available"))),
    )
    return CoverageBlock("operational_expenses", "Операционные расходы", 10, any(v for _, v in subs), subs)


def _financial_block(snap: dict) -> CoverageBlock:
    subs = (
        ("кредиты", bool(snap.get("fin_loans_available"))),
        ("лизинг", bool(snap.get("fin_leasing_available"))),
        ("проценты", bool(snap.get("fin_interest_available"))),
    )
    return CoverageBlock("financial_expenses", "Финансовые расходы", 8, any(v for _, v in subs), subs)


def _inventory_block(snap: dict) -> CoverageBlock:
    inv = bool(snap.get("inventory_signals_available"))
    subs = (
        ("остатки", inv),
        ("закупки", bool(snap.get("procurement_available"))),
        ("оборачиваемость", bool(snap.get("turnover_available"))),
        ("замороженный капитал", bool(snap.get("frozen_capital_available"))),
    )
    return CoverageBlock("inventory_procurement", "Остатки и закупки", 10, any(v for _, v in subs), subs)


def _included_labels(blocks: tuple[CoverageBlock, ...]) -> tuple[str, ...]:
    labels: list[str] = []
    for block in blocks:
        if not block.available:
            continue
        for name, ok in block.sub_items:
            if ok:
                labels.append(name)
    return tuple(dict.fromkeys(labels))


def _excluded_labels(blocks: tuple[CoverageBlock, ...]) -> tuple[str, ...]:
    out: list[str] = []
    for block in blocks:
        if block.available:
            continue
        if block.block_id == "marketplace_promotion":
            out.append("расходы на продвижение маркетплейса")
        elif block.block_id == "external_marketing":
            out.append("внешняя реклама")
        elif block.block_id == "tax":
            out.append("налоги")
        elif block.block_id == "operational_expenses":
            out.append("зарплаты и прочие операционные расходы")
        elif block.block_id == "financial_expenses":
            out.append("кредиты и финансовые расходы")
        elif block.block_id == "inventory_procurement":
            out.append("остатки и закупки")
    return tuple(dict.fromkeys(out))


def _root_cause_confidence(
    snap: dict,
    deep: list[str],
    headline: str | None,
    ad_available: bool,
) -> tuple[dict, ...]:
    text = (" ".join(deep) + " " + str(headline or "")).lower()
    causes: list[dict] = []

    if "объём" in text or "объем" in text:
        conf = 0.91 if "главный фактор" in text else 0.82
        causes.append(
            {
                "cause": "снижение/рост объёма продаж",
                "reason_confidence": conf,
                "status": "confirmed",
            }
        )

    if "средний чек" in text:
        causes.append(
            {
                "cause": "изменение среднего чека",
                "reason_confidence": 0.85,
                "status": "confirmed",
            }
        )

    ret_delta = _dec(snap.get("return_rate_delta_pp"))
    if ret_delta is not None and abs(ret_delta) >= Decimal("1"):
        causes.append(
            {
                "cause": "рост/снижение возвратов",
                "reason_confidence": round(min(0.92, 0.7 + float(abs(ret_delta)) / 50), 2),
                "status": "confirmed",
            }
        )
    elif snap.get("return_rate_pct") is not None:
        causes.append(
            {
                "cause": "уровень возвратов",
                "reason_confidence": 0.76,
                "status": "confirmed",
            }
        )

    if "микса sku" in text or ("sku" in text and "выруч" in text):
        causes.append(
            {
                "cause": "структура продаж по SKU",
                "reason_confidence": 0.84,
                "status": "confirmed",
            }
        )

    if ad_available and _has_positive(snap.get("ad_spend_total")):
        causes.append(
            {
                "cause": "влияние рекламы",
                "reason_confidence": 0.75,
                "status": "confirmed",
            }
        )
    else:
        causes.append(
            {
                "cause": "влияние рекламы",
                "reason_confidence": None,
                "status": "unknown",
                "note": "неизвестно (данные отсутствуют)",
            }
        )

    return tuple(causes)


def _upload_priorities(blocks: tuple[CoverageBlock, ...], snap: dict) -> tuple[str, ...]:
    by_id = {b.block_id: b for b in blocks}
    out: list[str] = []
    if not by_id["marketplace_promotion"].available:
        out.append(_UPLOAD_PRIORITY[0])
    cov = _dec(snap.get("cost_coverage_pct"))
    if cov is None or cov < Decimal("100"):
        out.append(_UPLOAD_PRIORITY[1])
    if not by_id["tax"].available:
        out.append(_UPLOAD_PRIORITY[2])
    if not by_id["operational_expenses"].available:
        out.append(_UPLOAD_PRIORITY[3])
    if not by_id["inventory_procurement"].available:
        out.append(_UPLOAD_PRIORITY[4])
    return tuple(dict.fromkeys(out))


def _executive_summary_v2(
    blocks: tuple[CoverageBlock, ...],
    root_causes: tuple[dict, ...],
    upload: tuple[str, ...],
) -> dict:
    confirmed = [
        f"{c['cause']} — {c['reason_confidence']:.2f}"
        for c in root_causes
        if c.get("status") == "confirmed" and c.get("reason_confidence") is not None
    ]
    unknown = [
        c["cause"] + (f" — {c.get('note')}" if c.get("note") else "")
        for c in root_causes
        if c.get("status") == "unknown"
    ]
    for block in blocks:
        if block.available:
            continue
        if block.block_id == "tax" and "налог" not in " ".join(unknown):
            unknown.append("налоговая нагрузка — данные отсутствуют")
        if block.block_id == "operational_expenses" and not any("операцион" in u for u in unknown):
            unknown.append("операционные расходы — данные отсутствуют")
    return {
        "what_we_know": confirmed[:6],
        "what_we_cannot_assess": unknown[:6],
        "recommended_uploads": list(upload),
    }


def _analysis_limitations(included: tuple[str, ...], excluded: tuple[str, ...]) -> str:
    inc = ", ".join(included[:12]) if included else "нет данных"
    exc = ", ".join(excluded[:8]) if excluded else "нет"
    return (
        "### Ограничения анализа\n\n"
        f"В анализ включены: {inc}.\n\n"
        f"В анализ НЕ включены: {exc}.\n\n"
        "Поэтому рекомендации относятся только к данным, доступным системе.\n"
        "При добавлении отсутствующих данных выводы AI могут измениться."
    )


def _seller_usefulness_score(
    coverage_score: float,
    snap: dict,
    root_causes: tuple[dict, ...],
) -> float:
    confirmed = sum(1 for c in root_causes if c.get("status") == "confirmed")
    base = coverage_score * 0.55
    causal_bonus = min(25.0, confirmed * 5.0)
    action_bonus = 10.0 if snap.get("analyst_actions") or snap.get("deep_insights") else 0.0
    return round(min(100.0, base + causal_bonus + action_bonus), 1)
