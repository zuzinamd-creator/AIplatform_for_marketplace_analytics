"""Build governed analytical intelligence package from deterministic DTOs."""

from __future__ import annotations

from decimal import Decimal

from app.dto.ai_analytics_dto import GroundedContextDTO
from app.dto.analytics_dto import AIInsightInputDTO
from app.dto.domain_analyst_dto import (
    AdsAnalyticsSlice,
    AnalyticalIntelligencePackage,
    AnomalyAnalyticsSlice,
    FunnelAnalyticsSlice,
    InventoryAnalyticsSlice,
    MarketplaceComparisonSlice,
    SalesAnalyticsSlice,
)


def build_analytical_package(
    *,
    grounded: GroundedContextDTO,
    insight: AIInsightInputDTO | None,
) -> AnalyticalIntelligencePackage:
    """Slice pre-computed KPIs — no metric computation in this layer."""
    sales = SalesAnalyticsSlice()
    ads = AdsAnalyticsSlice()
    funnel = FunnelAnalyticsSlice()
    inventory = InventoryAnalyticsSlice()
    marketplace = MarketplaceComparisonSlice()
    anomaly = AnomalyAnalyticsSlice()
    report_id = None

    if insight is not None:
        report_id = insight.context.report_id
        m = insight.metrics
        sales = SalesAnalyticsSlice(
            sku_count=m.sku_count,
            total_revenue=m.total_revenue,
            total_profit=m.total_profit,
            margin=m.margin,
            top_skus=tuple(m.top_skus_summary),
        )
        ads = AdsAnalyticsSlice(
            marketplace_type=insight.context.marketplace_type,
            ad_spend_available=False,
            notes="Ad spend KPIs not present in governed insight DTO; advisory limited to marketplace context.",
        )
        top_rev = Decimal("0")
        if m.top_skus_summary:
            for sku in m.top_skus_summary:
                if sku.revenue is not None and sku.revenue > top_rev:
                    top_rev = sku.revenue
            total = m.total_revenue or Decimal("0")
            concentration = (
                (top_rev / total * Decimal("100")) if total > 0 else None
            )
        else:
            concentration = None
        funnel = FunnelAnalyticsSlice(sku_count=m.sku_count, top_sku_concentration=concentration)
        inventory = InventoryAnalyticsSlice(
            sku_count=m.sku_count,
            inventory_signals_available=False,
        )
        marketplace = MarketplaceComparisonSlice(
            marketplace_type=insight.context.marketplace_type,
            single_marketplace_report=True,
        )
        anomaly = AnomalyAnalyticsSlice(anomalies=tuple(insight.anomalies))

    return AnalyticalIntelligencePackage(
        semantics_version=grounded.semantics_version,
        data_as_of=grounded.data_as_of,
        report_id=report_id,
        grounded=grounded,
        insight=insight,
        sales=sales,
        ads=ads,
        funnel=funnel,
        inventory=inventory,
        marketplace=marketplace,
        anomaly=anomaly,
        evidence_refs=grounded.evidence,
    )
