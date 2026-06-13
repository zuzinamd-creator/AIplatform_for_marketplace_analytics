"""Revenue change analyst — period-over-period revenue and profit shifts."""

from __future__ import annotations

from decimal import Decimal

from app.ai.analysts.base import DomainAnalystBase
from app.ai.analysts.governed_signals import REVENUE_DROP_THRESHOLD, REVENUE_GROWTH_THRESHOLD
from app.dto.domain_analyst_dto import (
    AnalyticalIntelligencePackage,
    DomainAnalystId,
    DomainAnalystOutputDTO,
    DomainFindingDTO,
)


class RevenueChangeAnalyst(DomainAnalystBase):
    analyst_id = DomainAnalystId.REVENUE_CHANGE

    def analyze(self, package: AnalyticalIntelligencePackage) -> DomainAnalystOutputDTO:
        rc = package.revenue_change
        evidence = self._evidence_from_package(package)
        findings: list[DomainFindingDTO] = []

        if not rc.compare_available:
            return self._output([], insufficient_data=True)

        rev = rc.revenue_change_pct
        if rev is not None and rev <= REVENUE_DROP_THRESHOLD:
            driver = rc.sku_revenue_drivers[0] if rc.sku_revenue_drivers else None
            action = f"Выручка упала на {abs(rev):.1f}% vs период сравнения."
            if driver:
                action += (
                    f" Главный вклад SKU {driver.sku} ({driver.amount:+.0f} ₽). "
                    f"Проверьте наличие, цену и рекламу по этому артикулу."
                )
            else:
                action += " Сверьте остатки, цены и рекламные кампании по топ-SKU."
            findings.append(
                DomainFindingDTO(
                    finding_id="revenue_drop",
                    statement=f"Revenue declined {rev:.1f}% vs comparison period.",
                    confidence=Decimal("0.91"),
                    severity="high" if rev <= Decimal("-20") else "medium",
                    evidence_refs=evidence,
                    recommended_actions=[action],
                )
            )
        elif rev is not None and rev >= REVENUE_GROWTH_THRESHOLD:
            driver = rc.sku_revenue_drivers[0] if rc.sku_revenue_drivers else None
            action = f"Выручка выросла на {rev:.1f}% — закрепите успех."
            if driver and driver.amount > 0:
                action += f" Драйвер: SKU {driver.sku} (+{driver.amount:.0f} ₽)."
            findings.append(
                DomainFindingDTO(
                    finding_id="revenue_growth",
                    statement=f"Revenue grew {rev:.1f}% vs comparison period.",
                    confidence=Decimal("0.88"),
                    severity="low",
                    evidence_refs=evidence,
                    recommended_actions=[action],
                )
            )

        prof = rc.profit_change_pct
        if prof is not None and prof <= REVENUE_DROP_THRESHOLD:
            findings.append(
                DomainFindingDTO(
                    finding_id="profit_drop",
                    statement=f"Profit declined {prof:.1f}% vs comparison period.",
                    confidence=Decimal("0.90"),
                    severity="high",
                    evidence_refs=evidence,
                    recommended_actions=[
                        f"Прибыль упала на {abs(prof):.1f}% — проверьте себестоимость, "
                        "комиссию и логистику по SKU с падением маржи."
                    ],
                )
            )

        for driver in rc.sku_revenue_drivers[:2]:
            if abs(driver.amount) >= Decimal("1000"):
                fid = "revenue_sku_driver_drop" if driver.amount < 0 else "revenue_sku_driver_gain"
                findings.append(
                    DomainFindingDTO(
                        finding_id=f"{fid}_{driver.sku[:24]}",
                        statement=(
                            f"SKU {driver.sku} revenue delta {driver.amount:+.0f} ₽ "
                            f"({driver.share_pct:+.1f}%) vs comparison."
                        ),
                        confidence=Decimal("0.86"),
                        severity="medium",
                        evidence_refs=evidence + [f"sku:{driver.sku}"],
                        recommended_actions=[
                            f"SKU {driver.sku}: изменение выручки {driver.amount:+.0f} ₽ — "
                            "оцените цену, остатки и рекламу по этой позиции."
                        ],
                    )
                )

        return self._output(findings)
