"""Logistics domain analyst — share, growth, SKU anomalies."""

from __future__ import annotations

from decimal import Decimal

from app.ai.analysts.base import DomainAnalystBase
from app.ai.analysts.governed_signals import LOGISTICS_HIGH_SHARE, LOGISTICS_SKU_THRESHOLD
from app.dto.domain_analyst_dto import (
    AnalyticalIntelligencePackage,
    DomainAnalystId,
    DomainAnalystOutputDTO,
    DomainFindingDTO,
)


class LogisticsAnalyst(DomainAnalystBase):
    analyst_id = DomainAnalystId.LOGISTICS

    def analyze(self, package: AnalyticalIntelligencePackage) -> DomainAnalystOutputDTO:
        lg = package.logistics
        evidence = self._evidence_from_package(package)
        findings: list[DomainFindingDTO] = []

        if lg.logistics_share_pct is None:
            return self._output([], insufficient_data=True)

        share = lg.logistics_share_pct
        if share >= LOGISTICS_HIGH_SHARE:
            sku_hint = ", ".join(s.sku for s in lg.high_burden_skus[:3])
            action = (
                f"Логистика составляет {share:.1f}% выручки (норма ~{LOGISTICS_HIGH_SHARE:.0f}%). "
                f"Проверьте тарифы WB и габариты SKU"
            )
            if sku_hint:
                action += f" {sku_hint}."
            else:
                action += " с наибольшей долей логистики."
            findings.append(
                DomainFindingDTO(
                    finding_id="logistics_high_share",
                    statement=(
                        f"Logistics burden {share:.1f}% of revenue exceeds "
                        f"{LOGISTICS_HIGH_SHARE:.0f}% benchmark."
                    ),
                    confidence=Decimal("0.90"),
                    severity="high" if share >= Decimal("20") else "medium",
                    evidence_refs=evidence,
                    recommended_actions=[action],
                )
            )

        if lg.logistics_share_delta_pp is not None and lg.logistics_share_delta_pp >= Decimal("3"):
            findings.append(
                DomainFindingDTO(
                    finding_id="logistics_share_growth",
                    statement=(
                        f"Logistics share grew {lg.logistics_share_delta_pp:.1f} p.p. "
                        "vs comparison period."
                    ),
                    confidence=Decimal("0.86"),
                    severity="medium",
                    evidence_refs=evidence,
                    recommended_actions=[
                        f"Доля логистики выросла на {lg.logistics_share_delta_pp:.1f} п.п. — "
                        "сверьте новые тарифы доставки и объём возвратов на склад."
                    ],
                )
            )

        for sku in lg.high_burden_skus:
            if sku.share_pct >= LOGISTICS_SKU_THRESHOLD:
                findings.append(
                    DomainFindingDTO(
                        finding_id=f"logistics_sku_anomaly_{sku.sku[:32]}",
                        statement=(
                            f"SKU {sku.sku} logistics {sku.share_pct:.1f}% of its revenue "
                            f"({sku.amount:.0f} ₽)."
                        ),
                        confidence=Decimal("0.88"),
                        severity="high",
                        evidence_refs=evidence + [f"sku:{sku.sku}"],
                        recommended_actions=[
                            f"На SKU {sku.sku} логистика {sku.share_pct:.0f}% выручки — "
                            "проверьте упаковку, габариты V/W/H и тариф склада."
                        ],
                    )
                )

        return self._output(findings)
