"""Returns domain analyst — return rate, growth, SKU leaders."""

from __future__ import annotations

from decimal import Decimal

from app.ai.analysts.base import DomainAnalystBase
from app.ai.analysts.governed_signals import RETURNS_HIGH_RATE
from app.dto.domain_analyst_dto import (
    AnalyticalIntelligencePackage,
    DomainAnalystId,
    DomainAnalystOutputDTO,
    DomainFindingDTO,
)


class ReturnsAnalyst(DomainAnalystBase):
    analyst_id = DomainAnalystId.RETURNS

    def analyze(self, package: AnalyticalIntelligencePackage) -> DomainAnalystOutputDTO:
        rt = package.returns
        evidence = self._evidence_from_package(package)
        findings: list[DomainFindingDTO] = []

        if rt.return_rate_pct is None and not rt.top_return_skus:
            return self._output([], insufficient_data=True)

        rate = rt.return_rate_pct
        if rate is not None and rate >= RETURNS_HIGH_RATE:
            sku_hint = ", ".join(s.sku for s in rt.top_return_skus[:3])
            findings.append(
                DomainFindingDTO(
                    finding_id="returns_high_rate",
                    statement=f"Return rate {rate:.1f}% exceeds {RETURNS_HIGH_RATE:.0f}% threshold.",
                    confidence=Decimal("0.89"),
                    severity="high" if rate >= Decimal("15") else "medium",
                    evidence_refs=evidence,
                    recommended_actions=[
                        f"Возвраты {rate:.1f}% от выручки (норма <{RETURNS_HIGH_RATE:.0f}%). "
                        f"Проверьте карточки и качество SKU"
                        + (f": {sku_hint}." if sku_hint else ".")
                    ],
                )
            )

        if rt.return_rate_delta_pp is not None and rt.return_rate_delta_pp >= Decimal("3"):
            findings.append(
                DomainFindingDTO(
                    finding_id="returns_rate_growth",
                    statement=f"Return rate increased {rt.return_rate_delta_pp:.1f} p.p. vs prior period.",
                    confidence=Decimal("0.85"),
                    severity="medium",
                    evidence_refs=evidence,
                    recommended_actions=[
                        f"Доля возвратов выросла на {rt.return_rate_delta_pp:.1f} п.п. — "
                        "разберите причины по топ-SKU и отзывам."
                    ],
                )
            )

        for sku in rt.top_return_skus[:2]:
            if sku.share_pct >= Decimal("8"):
                findings.append(
                    DomainFindingDTO(
                        finding_id=f"returns_sku_leader_{sku.sku[:32]}",
                        statement=f"SKU {sku.sku} return burden {sku.share_pct:.1f}% of its revenue.",
                        confidence=Decimal("0.87"),
                        severity="medium",
                        evidence_refs=evidence + [f"sku:{sku.sku}"],
                        recommended_actions=[
                            f"SKU {sku.sku} — лидер по возвратам ({sku.share_pct:.0f}% выручки). "
                            "Проверьте размерную сетку, фото и описание."
                        ],
                    )
                )

        return self._output(findings)
