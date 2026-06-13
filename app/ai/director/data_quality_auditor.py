"""Level 0 — Data Quality Auditor (mandatory pre-layer)."""

from __future__ import annotations

from decimal import Decimal

from app.ai.director.coverage_v2 import assess_coverage_v2
from app.ai.director.dto import DataQualityAuditDTO, DomainExpertId

# Minimum completeness to allow an expert to run (dimension-level gate)
_EXPERT_REQUIRED_DIMENSIONS: dict[DomainExpertId, tuple[str, ...]] = {
    DomainExpertId.SALES: ("sales",),
    DomainExpertId.MARKETPLACE_ECONOMICS: ("marketplace_economics",),
    DomainExpertId.UNIT_ECONOMICS: ("cogs",),
    DomainExpertId.ADVERTISING: ("promotion",),
    DomainExpertId.PRODUCT_CARD: ("conversion", "ctr"),
    DomainExpertId.INVENTORY: ("inventory",),
    DomainExpertId.TAX: ("tax",),
    DomainExpertId.OPERATING_COST: ("opex",),
}

_ALL_EXPERTS = list(DomainExpertId)


def run_data_quality_audit(snap: dict) -> DataQualityAuditDTO:
    """Determine coverage, penalties, and which domain experts may run."""
    v2 = assess_coverage_v2(snap)
    completeness_by_id = {d.dimension_id: d.completeness for d in v2.dimensions}

    allowed: list[str] = []
    blocked: list[str] = []
    for expert_id in _ALL_EXPERTS:
        required = _EXPERT_REQUIRED_DIMENSIONS.get(expert_id, ())
        if not required:
            blocked.append(expert_id.value)
            continue
        ok = all(completeness_by_id.get(dim, Decimal("0")) > 0 for dim in required)
        # Product card needs at least one of conversion OR ctr dimensions partially present
        if expert_id == DomainExpertId.PRODUCT_CARD:
            ok = completeness_by_id.get("conversion", Decimal("0")) > 0 or completeness_by_id.get(
                "ctr", Decimal("0")
            ) > 0
        if ok:
            allowed.append(expert_id.value)
        else:
            blocked.append(expert_id.value)

    # Confidence penalty: up to 0.45 when coverage is low
    penalty = min(
        Decimal("0.45"),
        (Decimal("100") - v2.coverage_score) / Decimal("100") * Decimal("0.45"),
    ).quantize(Decimal("0.01"))

    missing = [d.label for d in v2.dimensions if d.completeness < Decimal("1")]

    return DataQualityAuditDTO(
        coverage_score=v2.coverage_score,
        coverage_version="v2",
        missing_blocks=missing,
        confidence_penalty=penalty,
        allowed_analysts=allowed,
        blocked_analysts=blocked,
        coverage_formula=v2.formula,
    )
