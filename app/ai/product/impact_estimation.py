"""Measurable impact estimation — ranges only, never fabricated exact KPIs."""

from __future__ import annotations

from dataclasses import dataclass

from app.dto.ai_analytics_dto import GroundedContextDTO, ValidatedInsightDTO
from app.dto.ai_intelligence_dto import ScoredRecommendationDTO


@dataclass(frozen=True)
class ImpactEstimateDTO:
    category: str
    range_label: str
    confidence_band: str
    evidence_refs: list[str]
    uncertainty_note: str


@dataclass(frozen=True)
class MeasurableImpactDTO:
    estimates: list[ImpactEstimateDTO]
    summary: str
    do_not_trust_exact_amounts: bool = True


def build_measurable_impact(
    *,
    scored: ScoredRecommendationDTO,
    validated: ValidatedInsightDTO,
    grounded: GroundedContextDTO,
    evidence_refs: list[str],
) -> MeasurableImpactDTO:
    """Qualitative impact bands derived from governed metrics only."""
    estimates: list[ImpactEstimateDTO] = []
    metrics = grounded.metrics_snapshot or {}
    revenue = metrics.get("total_revenue")
    margin = metrics.get("margin")
    wf = validated.workflow.value

    if wf in ("anomaly_explanation", "risk_detection"):
        estimates.append(
            ImpactEstimateDTO(
                category="data_trust",
                range_label="high risk to decision quality until resolved",
                confidence_band="medium-high",
                evidence_refs=evidence_refs[:5],
                uncertainty_note="Cannot quantify revenue until anomalies are fixed.",
            )
        )
    elif revenue is not None and wf == "revenue_insight":
        estimates.append(
            ImpactEstimateDTO(
                category="revenue_recovery",
                range_label="moderate upside if listing/pricing fix validated",
                confidence_band="medium",
                evidence_refs=evidence_refs[:5],
                uncertainty_note="Range only — based on governed report totals, not a forecast.",
            )
        )
    if margin is not None:
        try:
            m = float(margin)
            if m < 0.15:
                estimates.append(
                    ImpactEstimateDTO(
                        category="margin_improvement",
                        range_label="meaningful margin lift possible after cost/price review",
                        confidence_band="medium",
                        evidence_refs=evidence_refs[:3],
                        uncertainty_note="Requires complete cost data in analytics.",
                    )
                )
        except (TypeError, ValueError):
            pass

    if wf == "inventory_insight":
        estimates.append(
            ImpactEstimateDTO(
                category="stockout_prevention",
                range_label="reduced lost-sales risk if stock aligned to top SKUs",
                confidence_band="low-medium",
                evidence_refs=evidence_refs[:3],
                uncertainty_note="Inventory KPIs limited unless snapshots are imported.",
            )
        )

    if not estimates:
        estimates.append(
            ImpactEstimateDTO(
                category="operational",
                range_label="incremental improvement after evidence check",
                confidence_band="low",
                evidence_refs=evidence_refs[:3],
                uncertainty_note="Insufficient governed metrics for tighter range.",
            )
        )

    summary = "; ".join(e.range_label for e in estimates[:2])
    return MeasurableImpactDTO(estimates=estimates, summary=summary)
