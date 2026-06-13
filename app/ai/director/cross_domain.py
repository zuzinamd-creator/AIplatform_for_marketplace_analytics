"""Level 2 — Cross-Domain Analysts (consume Domain Expert outputs, not raw KPI)."""

from __future__ import annotations

from decimal import Decimal

from app.ai.director.dto import (
    ActionableFindingDTO,
    CrossDomainAnalystId,
    CrossDomainOutputDTO,
    DomainExpertId,
    DomainExpertOutputDTO,
)

_UPSTREAM: dict[CrossDomainAnalystId, tuple[DomainExpertId, ...]] = {
    CrossDomainAnalystId.GROWTH: (
        DomainExpertId.SALES,
        DomainExpertId.ADVERTISING,
        DomainExpertId.PRODUCT_CARD,
    ),
    CrossDomainAnalystId.PROFIT: (
        DomainExpertId.SALES,
        DomainExpertId.MARKETPLACE_ECONOMICS,
        DomainExpertId.UNIT_ECONOMICS,
        DomainExpertId.TAX,
        DomainExpertId.OPERATING_COST,
    ),
    CrossDomainAnalystId.RISK: (
        DomainExpertId.SALES,
        DomainExpertId.INVENTORY,
        DomainExpertId.UNIT_ECONOMICS,
    ),
}

_QUESTIONS = {
    CrossDomainAnalystId.GROWTH: "Почему изменились продажи?",
    CrossDomainAnalystId.PROFIT: "Почему изменилась прибыль бизнеса?",
    CrossDomainAnalystId.RISK: "Какие риски есть у бизнеса?",
}


def run_cross_domain_analysts(
    domain_outputs: list[DomainExpertOutputDTO],
) -> list[CrossDomainOutputDTO]:
    by_id = {d.analyst_id: d for d in domain_outputs}
    results: list[CrossDomainOutputDTO] = []

    for analyst_id, upstream in _UPSTREAM.items():
        ran_upstream = [by_id[u] for u in upstream if u in by_id and by_id[u].ran]
        if not ran_upstream:
            results.append(
                CrossDomainOutputDTO(
                    analyst_id=analyst_id,
                    ran=False,
                    skip_reason="no upstream domain expert ran",
                    question=_QUESTIONS[analyst_id],
                    upstream_analysts=[u.value for u in upstream],
                )
            )
            continue

        findings = _synthesize(analyst_id, ran_upstream)
        conf = (
            sum(f.confidence for f in findings) / Decimal(len(findings))
            if findings
            else Decimal("0.4")
        )
        results.append(
            CrossDomainOutputDTO(
                analyst_id=analyst_id,
                ran=bool(findings),
                skip_reason=None if findings else "insufficient upstream findings",
                question=_QUESTIONS[analyst_id],
                findings=findings,
                upstream_analysts=[u.analyst_id.value for u in ran_upstream],
                overall_confidence=min(Decimal("1"), conf),
            )
        )

    return results


def _synthesize(
    analyst_id: CrossDomainAnalystId,
    upstream: list[DomainExpertOutputDTO],
) -> list[ActionableFindingDTO]:
    all_findings = [f for u in upstream for f in u.findings]
    if not all_findings:
        return []

    if analyst_id == CrossDomainAnalystId.GROWTH:
        sales = next((u for u in upstream if u.analyst_id == DomainExpertId.SALES), None)
        ads = next((u for u in upstream if u.analyst_id == DomainExpertId.ADVERTISING), None)
        if sales and sales.findings and (not ads or not ads.ran):
            top = sales.findings[0]
            return [
                ActionableFindingDTO(
                    finding_id="growth_sales_without_ads",
                    finding="Изменение продаж объясняется доступными sales-сигналами; реклама не измерена.",
                    root_cause=top.root_cause,
                    impact_estimate="Рост/падение продаж без данных о рекламном трафике",
                    recommended_action=(
                        "Сверьте динамику продаж с остатками и ценой; загрузите рекламные отчёты "
                        "для проверки гипотезы о влиянии продвижения."
                    ),
                    confidence=top.confidence * Decimal("0.85"),
                    severity="medium",
                )
            ]
        if sales and sales.findings:
            return [
                ActionableFindingDTO(
                    finding_id="growth_combined",
                    finding="Сопоставлены выводы Sales и Advertising experts.",
                    root_cause="; ".join(f.root_cause[:120] for f in sales.findings[:2]),
                    impact_estimate="cross-domain growth synthesis",
                    recommended_action=sales.findings[0].recommended_action,
                    confidence=sales.findings[0].confidence,
                    severity="medium",
                )
            ]

    if analyst_id == CrossDomainAnalystId.PROFIT:
        parts = [f for u in upstream for f in u.findings][:3]
        if parts:
            return [
                ActionableFindingDTO(
                    finding_id="profit_cross_domain",
                    finding="Прибыль изменилась под влиянием нескольких факторов из доступных доменов.",
                    root_cause="; ".join(p.root_cause[:100] for p in parts),
                    impact_estimate="marketplace + unit economics synthesis",
                    recommended_action=parts[0].recommended_action,
                    confidence=min(p.confidence for p in parts),
                    severity="high",
                )
            ]

    if analyst_id == CrossDomainAnalystId.RISK:
        risks: list[ActionableFindingDTO] = []
        for f in all_findings:
            low = f.finding.lower()
            if any(k in low for k in ("концентрац", "убыточ", "возврат", "out of stock", "остат")):
                risks.append(
                    f.model_copy(
                        update={
                            "finding_id": f"risk_{f.finding_id}"[:64],
                            "impact_estimate": "business risk signal",
                        }
                    )
                )
        return risks[:5]

    return []
