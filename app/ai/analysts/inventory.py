"""Inventory domain analyst — stock and discrepancy signals from governed DTOs."""

from __future__ import annotations

from decimal import Decimal

from app.ai.analysts.base import DomainAnalystBase
from app.dto.domain_analyst_dto import (
    AnalyticalIntelligencePackage,
    DomainAnalystId,
    DomainAnalystOutputDTO,
    DomainFindingDTO,
)


class InventoryAnalyst(DomainAnalystBase):
    analyst_id = DomainAnalystId.INVENTORY

    def analyze(self, package: AnalyticalIntelligencePackage) -> DomainAnalystOutputDTO:
        inv = package.inventory
        evidence = self._evidence_from_package(package)

        if not inv.inventory_signals_available:
            return self._output(
                [
                    DomainFindingDTO(
                        finding_id="inventory_limited_signals",
                        statement=(
                            f"Governed package lists {inv.sku_count} SKUs without inventory loss KPIs; "
                            "inventory advisory is limited to catalog scale."
                        ),
                        confidence=Decimal("0.6"),
                        severity="low",
                        evidence_refs=evidence,
                        recommended_actions=[
                            "Подключите снимки остатков в ETL для советов по складу и потерям.",
                        ],
                    )
                ],
                insufficient_data=True,
            )

        return self._output([])
