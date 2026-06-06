"""Marketplace comparison analyst — single-marketplace context advisory."""

from __future__ import annotations

from decimal import Decimal

from app.ai.analysts.base import DomainAnalystBase
from app.dto.domain_analyst_dto import (
    AnalyticalIntelligencePackage,
    DomainAnalystId,
    DomainAnalystOutputDTO,
    DomainFindingDTO,
)


class MarketplaceComparisonAnalyst(DomainAnalystBase):
    analyst_id = DomainAnalystId.MARKETPLACE_COMPARISON

    def analyze(self, package: AnalyticalIntelligencePackage) -> DomainAnalystOutputDTO:
        m = package.marketplace
        evidence = self._evidence_from_package(package)

        if not m.marketplace_type:
            return self._output([], insufficient_data=True)

        findings = [
            DomainFindingDTO(
                finding_id="mp_context",
                statement=(
                    f"Current report is scoped to marketplace '{m.marketplace_type}' "
                    f"(single_report={m.single_marketplace_report})."
                ),
                confidence=Decimal("0.9"),
                severity="low",
                evidence_refs=evidence,
                recommended_actions=[
                    "Загрузите отчёты других маркетплейсов для сравнительного анализа.",
                ],
            )
        ]
        return self._output(findings)
