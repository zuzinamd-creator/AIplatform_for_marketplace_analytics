"""Base domain analyst — structured JSON over governed DTOs only."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from app.dto.domain_analyst_dto import (
    AnalyticalIntelligencePackage,
    DomainAnalystId,
    DomainAnalystOutputDTO,
    DomainFindingDTO,
)


class DomainAnalystBase(ABC):
    analyst_id: DomainAnalystId
    contract_version: str = "2.0.0"

    @abstractmethod
    def analyze(self, package: AnalyticalIntelligencePackage) -> DomainAnalystOutputDTO:
        """Produce structured findings from governed slices (no KPI computation)."""

    def _output(
        self,
        findings: list[DomainFindingDTO],
        *,
        insufficient_data: bool = False,
    ) -> DomainAnalystOutputDTO:
        if not findings:
            conf = Decimal("0.3") if insufficient_data else Decimal("0.5")
            return DomainAnalystOutputDTO(
                analyst_id=self.analyst_id,
                contract_version=self.contract_version,
                findings=[],
                overall_confidence=conf,
                insufficient_data=insufficient_data,
            )
        confs = [f.confidence for f in findings]
        overall = sum(confs) / Decimal(len(confs))
        return DomainAnalystOutputDTO(
            analyst_id=self.analyst_id,
            contract_version=self.contract_version,
            findings=findings,
            overall_confidence=min(Decimal("1"), overall),
            insufficient_data=insufficient_data,
        )

    def _evidence_from_package(self, package: AnalyticalIntelligencePackage) -> list[str]:
        refs: list[str] = []
        for ev in package.evidence_refs:
            refs.append(f"{ev.source_type}:{ev.source_id}")
        if package.report_id is not None:
            refs.append(f"report:{package.report_id}")
        return refs[:10]
