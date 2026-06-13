"""Concentration analyst — dependency on 1–3 SKUs."""

from __future__ import annotations

from decimal import Decimal

from app.ai.analysts.base import DomainAnalystBase
from app.ai.analysts.governed_signals import CONCENTRATION_TOP1, CONCENTRATION_TOP3
from app.dto.domain_analyst_dto import (
    AnalyticalIntelligencePackage,
    DomainAnalystId,
    DomainAnalystOutputDTO,
    DomainFindingDTO,
)


class ConcentrationAnalyst(DomainAnalystBase):
    analyst_id = DomainAnalystId.CONCENTRATION

    def analyze(self, package: AnalyticalIntelligencePackage) -> DomainAnalystOutputDTO:
        c = package.concentration
        evidence = self._evidence_from_package(package)
        findings: list[DomainFindingDTO] = []

        if c.top1_share_pct is None:
            return self._output([], insufficient_data=True)

        top1 = c.top1_share_pct
        top3 = c.top3_share_pct or top1
        skus = ", ".join(c.top_skus[:3])

        if top1 >= CONCENTRATION_TOP1:
            findings.append(
                DomainFindingDTO(
                    finding_id="concentration_top1_risk",
                    statement=(
                        f"Top SKU concentration {top1:.1f}% of revenue — "
                        "single-SKU dependency risk."
                    ),
                    confidence=Decimal("0.91"),
                    severity="high" if top1 >= Decimal("67") else "medium",
                    evidence_refs=evidence,
                    recommended_actions=[
                        f"{top1:.0f}% выручки приходится на один SKU"
                        + (f" ({c.top_skus[0]})" if c.top_skus else "")
                        + " — риск концентрации. Продвигайте другие позиции и "
                        "страхуйте остатки лидера."
                    ],
                )
            )
        elif top3 >= CONCENTRATION_TOP3:
            findings.append(
                DomainFindingDTO(
                    finding_id="concentration_top3_risk",
                    statement=f"Top-3 SKUs account for {top3:.1f}% of revenue.",
                    confidence=Decimal("0.84"),
                    severity="medium",
                    evidence_refs=evidence,
                    recommended_actions=[
                        f"Топ-3 SKU ({skus}) дают {top3:.0f}% выручки — "
                        "диверсифицируйте ассортимент и рекламный бюджет."
                    ],
                )
            )

        return self._output(findings)
