"""Run all domain analysts over a governed analytical package."""

from __future__ import annotations

from app.ai.analysts.ads import AdsAnalyst
from app.ai.analysts.anomaly import AnomalyAnalyst
from app.ai.analysts.funnel import FunnelAnalyst
from app.ai.analysts.inventory import InventoryAnalyst
from app.ai.analysts.marketplace import MarketplaceComparisonAnalyst
from app.ai.analysts.sales import SalesAnalyst
from app.dto.domain_analyst_dto import AnalyticalIntelligencePackage, DomainAnalystOutputDTO


def run_domain_analysts(package: AnalyticalIntelligencePackage) -> list[DomainAnalystOutputDTO]:
    analysts = (
        SalesAnalyst(),
        AdsAnalyst(),
        FunnelAnalyst(),
        InventoryAnalyst(),
        MarketplaceComparisonAnalyst(),
        AnomalyAnalyst(),
    )
    return [a.analyze(package) for a in analysts]
