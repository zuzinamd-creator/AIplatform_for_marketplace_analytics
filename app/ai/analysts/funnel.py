"""Funnel domain analyst — SKU concentration and catalog breadth."""

from __future__ import annotations

from decimal import Decimal

from app.ai.analysts.base import DomainAnalystBase
from app.dto.domain_analyst_dto import (
    AnalyticalIntelligencePackage,
    DomainAnalystId,
    DomainAnalystOutputDTO,
    DomainFindingDTO,
)


class FunnelAnalyst(DomainAnalystBase):
    analyst_id = DomainAnalystId.FUNNEL

    def analyze(self, package: AnalyticalIntelligencePackage) -> DomainAnalystOutputDTO:
        f = package.funnel
        evidence = self._evidence_from_package(package)
        findings: list[DomainFindingDTO] = []

        if f.sku_count == 0:
            return self._output([], insufficient_data=True)

        if f.top_sku_concentration is not None and f.top_sku_concentration > Decimal("60"):
            findings.append(
                DomainFindingDTO(
                    finding_id="funnel_concentration",
                    statement=(
                        f"Top SKU concentration ~{f.top_sku_concentration:.1f}% of governed revenue "
                        "— revenue funnel is highly concentrated."
                    ),
                    confidence=Decimal("0.82"),
                    severity="medium",
                    evidence_refs=evidence,
                    recommended_actions=[
                        "Снизьте зависимость от одного SKU — продвигайте другие позиции.",
                    ],
                )
            )
        elif f.sku_count >= 5:
            findings.append(
                DomainFindingDTO(
                    finding_id="funnel_breadth_ok",
                    statement=f"Catalog breadth ({f.sku_count} SKUs) supports distributed funnel risk.",
                    confidence=Decimal("0.75"),
                    severity="low",
                    evidence_refs=evidence,
                    recommended_actions=["Отслеживайте конверсию по группам SKU в аналитике."],
                )
            )

        return self._output(findings)
