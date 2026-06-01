"""Ads domain analyst — campaign spend advisory from governed signals only."""

from __future__ import annotations

from decimal import Decimal

from app.ai.analysts.base import DomainAnalystBase
from app.dto.domain_analyst_dto import (
    AnalyticalIntelligencePackage,
    DomainAnalystId,
    DomainAnalystOutputDTO,
    DomainFindingDTO,
)


class AdsAnalyst(DomainAnalystBase):
    analyst_id = DomainAnalystId.ADS

    def analyze(self, package: AnalyticalIntelligencePackage) -> DomainAnalystOutputDTO:
        a = package.ads
        evidence = self._evidence_from_package(package)

        if not a.ad_spend_available:
            return self._output(
                [
                    DomainFindingDTO(
                        finding_id="ads_no_governed_spend",
                        statement=(
                            "No governed ad-spend KPIs in current analytical package; "
                            "ads recommendations are context-only."
                        ),
                        confidence=Decimal("0.55"),
                        severity="low",
                        evidence_refs=evidence,
                        recommended_actions=[
                            "Import ad campaign reports before requesting spend optimization advisory.",
                        ],
                    )
                ],
                insufficient_data=True,
            )

        return self._output([])
