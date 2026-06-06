"""Sales domain analyst — revenue and margin interpretation."""

from __future__ import annotations

from decimal import Decimal

from app.ai.analysts.base import DomainAnalystBase
from app.dto.domain_analyst_dto import (
    AnalyticalIntelligencePackage,
    DomainAnalystId,
    DomainAnalystOutputDTO,
    DomainFindingDTO,
)


class SalesAnalyst(DomainAnalystBase):
    analyst_id = DomainAnalystId.SALES

    def analyze(self, package: AnalyticalIntelligencePackage) -> DomainAnalystOutputDTO:
        s = package.sales
        evidence = self._evidence_from_package(package)
        findings: list[DomainFindingDTO] = []

        if s.total_revenue is None and s.total_profit is None:
            return self._output([], insufficient_data=True)

        if s.total_revenue is not None and s.total_revenue > 0:
            findings.append(
                DomainFindingDTO(
                    finding_id="sales_revenue_present",
                    statement=f"Reported revenue {s.total_revenue} across {s.sku_count} SKUs (governed KPI).",
                    confidence=Decimal("0.92"),
                    severity="medium",
                    evidence_refs=evidence,
                    recommended_actions=[
                        "Сверьте вклад топ-SKU перед изменением цен.",
                        "Сравните период с предыдущим на Dashboard.",
                    ],
                )
            )

        if s.margin is not None and s.margin < Decimal("0.15"):
            findings.append(
                DomainFindingDTO(
                    finding_id="sales_low_margin",
                    statement=f"Margin {s.margin} is below typical healthy band — validate cost inputs.",
                    confidence=Decimal("0.88"),
                    severity="high",
                    evidence_refs=evidence,
                    recommended_actions=[
                        "Проверьте полноту импорта себестоимости перед решениями по марже.",
                    ],
                )
            )

        if s.top_skus:
            top = s.top_skus[0]
            findings.append(
                DomainFindingDTO(
                    finding_id="sales_top_sku",
                    statement=f"Leading SKU {top.internal_sku} in governed top-SKU list.",
                    confidence=Decimal("0.85"),
                    severity="low",
                    evidence_refs=evidence + [f"sku:{top.internal_sku}"],
                    recommended_actions=["Улучшите карточку и наличие на складе у лидера по выручке."],
                )
            )

        return self._output(findings)
