"""Anomaly domain analyst — ETL and data-quality anomalies from governed list."""

from __future__ import annotations

from decimal import Decimal

from app.ai.analysts.base import DomainAnalystBase
from app.dto.domain_analyst_dto import (
    AnalyticalIntelligencePackage,
    DomainAnalystId,
    DomainAnalystOutputDTO,
    DomainFindingDTO,
)


class AnomalyAnalyst(DomainAnalystBase):
    analyst_id = DomainAnalystId.ANOMALY

    def analyze(self, package: AnalyticalIntelligencePackage) -> DomainAnalystOutputDTO:
        anomalies = package.anomaly.anomalies
        evidence = self._evidence_from_package(package)
        findings: list[DomainFindingDTO] = []

        if not anomalies:
            findings.append(
                DomainFindingDTO(
                    finding_id="anomaly_none",
                    statement="No governed anomalies in current analytical package.",
                    confidence=Decimal("0.85"),
                    severity="low",
                    evidence_refs=evidence,
                    recommended_actions=[],
                )
            )
            return self._output(findings)

        for idx, anom in enumerate(anomalies[:10]):
            sev = anom.severity if anom.severity in ("low", "medium", "high") else "medium"
            findings.append(
                DomainFindingDTO(
                    finding_id=f"anomaly_{idx}_{anom.type}",
                    statement=anom.message[:512],
                    confidence=anom.confidence,
                    severity="critical" if sev == "high" else sev,  # type: ignore[arg-type]
                    evidence_refs=evidence + [f"anomaly:{anom.type}"],
                    recommended_actions=[
                        "Resolve data-quality issue in source report before trusting revenue KPIs.",
                    ],
                )
            )

        return self._output(findings)
