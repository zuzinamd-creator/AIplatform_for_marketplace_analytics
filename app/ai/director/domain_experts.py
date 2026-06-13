"""Level 1 — Domain Expert registry and adapters over existing analysts."""

from __future__ import annotations

from decimal import Decimal

from app.ai.analysts import build_analytical_package, run_domain_analysts
from app.ai.director.dto import (
    ActionableFindingDTO,
    DataQualityAuditDTO,
    DomainExpertId,
    DomainExpertOutputDTO,
)
from app.dto.ai_analytics_dto import GroundedContextDTO
from app.dto.analytics_dto import AIInsightInputDTO

# Maps new Operating Director experts → legacy domain analyst finding_id prefixes
_LEGACY_PREFIX_MAP: dict[DomainExpertId, tuple[str, ...]] = {
    DomainExpertId.SALES: (
        "sales_",
        "funnel_",
        "concentration_",
        "revenue_",
    ),
    DomainExpertId.MARKETPLACE_ECONOMICS: (
        "logistics_",
        "returns_",
    ),
    DomainExpertId.UNIT_ECONOMICS: (
        "sales_low_margin",
        "sales_top_sku",
    ),
    DomainExpertId.ADVERTISING: ("ads_",),
    DomainExpertId.INVENTORY: ("inventory_",),
    DomainExpertId.PRODUCT_CARD: ("product_card_",),
    DomainExpertId.TAX: ("tax_",),
    DomainExpertId.OPERATING_COST: ("opex_",),
}

_STUB_EXPERTS = frozenset(
    {
        DomainExpertId.PRODUCT_CARD,
        DomainExpertId.TAX,
        DomainExpertId.OPERATING_COST,
    }
)


def run_domain_experts(
    *,
    audit: DataQualityAuditDTO,
    grounded: GroundedContextDTO,
    insight_input: AIInsightInputDTO | None,
) -> list[DomainExpertOutputDTO]:
    """Run only allowed experts; blocked experts return skip_reason without findings."""
    allowed = set(audit.allowed_analysts)
    package = build_analytical_package(grounded=grounded, insight=insight_input)
    legacy_outputs = run_domain_analysts(package) if package.insight is not None else []

    findings_by_prefix: dict[str, list] = {}
    for out in legacy_outputs:
        for f in out.findings:
            findings_by_prefix.setdefault(f.finding_id, []).append((out, f))

    results: list[DomainExpertOutputDTO] = []
    for expert_id in DomainExpertId:
        if expert_id.value not in allowed:
            results.append(
                DomainExpertOutputDTO(
                    analyst_id=expert_id,
                    ran=False,
                    skip_reason=f"blocked: missing data ({expert_id.value})",
                )
            )
            continue

        if expert_id in _STUB_EXPERTS:
            results.append(
                DomainExpertOutputDTO(
                    analyst_id=expert_id,
                    ran=False,
                    skip_reason="not_implemented: awaiting data source integration",
                )
            )
            continue

        prefixes = _LEGACY_PREFIX_MAP.get(expert_id, ())
        findings: list[ActionableFindingDTO] = []
        for out in legacy_outputs:
            for f in out.findings:
                if not any(f.finding_id.startswith(p) or p in f.finding_id for p in prefixes):
                    continue
                action = (f.recommended_actions or ["Сверьте KPI на Dashboard и при необходимости скорректируйте."])[0]
                findings.append(
                    ActionableFindingDTO(
                        finding_id=f.finding_id,
                        finding=f.statement,
                        root_cause=f.statement[:512],
                        impact_estimate=f"severity={f.severity}",
                        recommended_action=action[:512],
                        confidence=f.confidence,
                        severity=f.severity if f.severity in ("low", "medium", "high", "critical") else "medium",
                        evidence_refs=f.evidence_refs,
                    )
                )

        # Deep insights bridge for marketplace economics / unit economics
        snap = grounded.metrics_snapshot or {}
        if expert_id == DomainExpertId.MARKETPLACE_ECONOMICS:
            findings.extend(_findings_from_deep(snap, keywords=("логистик", "комисс", "хранен", "штраф")))
        if expert_id == DomainExpertId.UNIT_ECONOMICS:
            findings.extend(_findings_from_deep(snap, keywords=("убыточ", "маржа", "себестоим")))

        conf = (
            sum(f.confidence for f in findings) / Decimal(len(findings))
            if findings
            else Decimal("0.3")
        )
        results.append(
            DomainExpertOutputDTO(
                analyst_id=expert_id,
                ran=True,
                findings=findings[:20],
                overall_confidence=min(Decimal("1"), conf),
            )
        )

    return results


def _findings_from_deep(snap: dict, *, keywords: tuple[str, ...]) -> list[ActionableFindingDTO]:
    out: list[ActionableFindingDTO] = []
    for idx, line in enumerate(snap.get("deep_insights") or []):
        low = str(line).lower()
        if not any(k in low for k in keywords):
            continue
        out.append(
            ActionableFindingDTO(
                finding_id=f"deep_{idx}",
                finding=str(line)[:512],
                root_cause=str(line)[:512],
                impact_estimate="deterministic deep insight",
                recommended_action=_action_from_line(str(line)),
                confidence=Decimal("0.88"),
                severity="medium",
            )
        )
    return out


def _action_from_line(line: str) -> str:
    verbs = ("проверьте", "сверьте", "рассмотрите", "добавьте", "импортируйте", "оцените")
    if any(v in line.lower() for v in verbs):
        return line[:512]
    return f"{line[:400]} — сверьте цифры и при необходимости скорректируйте в кабинете WB."
