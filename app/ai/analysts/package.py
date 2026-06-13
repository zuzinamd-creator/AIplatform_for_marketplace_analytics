"""Build governed analytical intelligence package from deterministic DTOs."""

from __future__ import annotations

from decimal import Decimal

from app.dto.ai_analytics_dto import GroundedContextDTO
from app.dto.analytics_dto import AIInsightInputDTO
from app.dto.domain_analyst_dto import (
    AdsAnalyticsSlice,
    AnalyticalIntelligencePackage,
    AnomalyAnalyticsSlice,
    ConcentrationAnalyticsSlice,
    FunnelAnalyticsSlice,
    InventoryAnalyticsSlice,
    InventorySkuRow,
    LogisticsAnalyticsSlice,
    MarketplaceComparisonSlice,
    ReturnsAnalyticsSlice,
    RevenueChangeAnalyticsSlice,
    SalesAnalyticsSlice,
    SkuSignalDTO,
)


def _dec(val: object) -> Decimal | None:
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except Exception:
        return None


def _sku_signals(raw: object) -> tuple[SkuSignalDTO, ...]:
    if not isinstance(raw, list):
        return ()
    out: list[SkuSignalDTO] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        sku = str(item.get("sku") or "")
        if not sku:
            continue
        out.append(
            SkuSignalDTO(
                sku=sku,
                share_pct=_dec(item.get("share_pct")) or Decimal("0"),
                amount=_dec(item.get("amount")) or Decimal("0"),
            )
        )
    return tuple(out)


def _inventory_sku_rows(raw: object) -> tuple[InventorySkuRow, ...]:
    if not isinstance(raw, list):
        return ()
    out: list[InventorySkuRow] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        sku = str(item.get("sku") or "")
        if not sku:
            continue
        out.append(
            InventorySkuRow(
                sku=sku,
                stock_units=int(item.get("stock_units") or 0),
                frozen_capital=_dec(item.get("frozen_capital")),
                days_since_last_sale=item.get("days_since_last_sale"),
                share_pct=_dec(item.get("share_pct")) or Decimal("0"),
            )
        )
    return tuple(out)


def _inventory_slice(snap: dict, sku_count: int) -> InventoryAnalyticsSlice:
    return InventoryAnalyticsSlice(
        sku_count=sku_count,
        total_skus=int(snap.get("inventory_total_skus") or sku_count or 0),
        inventory_signals_available=bool(snap.get("inventory_signals_available")),
        turnover_available=bool(snap.get("turnover_available")),
        frozen_capital_available=bool(snap.get("frozen_capital_available")),
        total_frozen_capital=_dec(snap.get("inventory_total_frozen_capital")),
        frozen_capital_share_pct=_dec(snap.get("inventory_frozen_capital_share_pct")),
        slow_mover_count=int(snap.get("inventory_slow_mover_count") or 0),
        dead_stock_count=int(snap.get("inventory_dead_stock_count") or 0),
        overstock_count=int(snap.get("inventory_overstock_count") or 0),
        stock_concentration_top3_pct=_dec(snap.get("inventory_stock_concentration_top3_pct")),
        inventory_risk_level=str(snap.get("inventory_risk_level") or "low"),
        top_slow_movers=_inventory_sku_rows(snap.get("inventory_slow_movers")),
        top_dead_stock=_inventory_sku_rows(snap.get("inventory_dead_stock")),
        top_frozen_capital_skus=_inventory_sku_rows(snap.get("inventory_top_frozen_capital")),
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
    logistics = LogisticsAnalyticsSlice()
    returns = ReturnsAnalyticsSlice()
    revenue_change = RevenueChangeAnalyticsSlice()
    concentration = ConcentrationAnalyticsSlice()
    report_id = None
    snap = dict(grounded.metrics_snapshot or {})
    sku_count = int(snap.get("sku_count") or 0)

    if insight is not None:
        report_id = insight.context.report_id
        m = insight.metrics
        sku_count = m.sku_count
        sales = SalesAnalyticsSlice(
            sku_count=m.sku_count,
            total_revenue=m.total_revenue,
            total_profit=m.total_profit,
            margin=m.margin,
            top_skus=tuple(m.top_skus_summary),
        )
        ads = AdsAnalyticsSlice(
            marketplace_type=insight.context.marketplace_type,
            ad_spend_available=bool(snap.get("ad_spend_available")),
            notes="Ad spend KPIs not present in governed insight DTO; advisory limited to marketplace context.",
        )
        top_rev = Decimal("0")
        if m.top_skus_summary:
            for sku in m.top_skus_summary:
                if sku.revenue is not None and sku.revenue > top_rev:
                    top_rev = sku.revenue
            total = m.total_revenue or Decimal("0")
            concentration_pct = (
                (top_rev / total * Decimal("100")) if total > 0 else None
            )
        else:
            concentration_pct = None
        funnel = FunnelAnalyticsSlice(sku_count=m.sku_count, top_sku_concentration=concentration_pct)
        marketplace = MarketplaceComparisonSlice(
            marketplace_type=insight.context.marketplace_type,
            single_marketplace_report=True,
        )
        anomaly = AnomalyAnalyticsSlice(anomalies=tuple(insight.anomalies))

    inventory = _inventory_slice(snap, sku_count)

    logistics = LogisticsAnalyticsSlice(
        logistics_share_pct=_dec(snap.get("logistics_share_pct")),
        logistics_share_delta_pp=_dec(snap.get("logistics_share_delta_pp")),
        high_burden_skus=_sku_signals(snap.get("logistics_high_burden_skus")),
    )
    returns = ReturnsAnalyticsSlice(
        return_rate_pct=_dec(snap.get("return_rate_pct")),
        return_rate_delta_pp=_dec(snap.get("return_rate_delta_pp")),
        top_return_skus=_sku_signals(snap.get("return_top_skus")),
    )
    revenue_change = RevenueChangeAnalyticsSlice(
        revenue_change_pct=_dec(snap.get("revenue_change_pct")),
        profit_change_pct=_dec(snap.get("profit_change_pct")),
        compare_available=bool(snap.get("compare_available")),
        sku_revenue_drivers=_sku_signals(snap.get("sku_revenue_drivers")),
    )
    concentration = ConcentrationAnalyticsSlice(
        top1_share_pct=_dec(snap.get("top1_share_pct")),
        top3_share_pct=_dec(snap.get("top3_share_pct")),
        top_skus=tuple(str(s) for s in (snap.get("concentration_top_skus") or [])),
    )

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
        logistics=logistics,
        returns=returns,
        revenue_change=revenue_change,
        concentration=concentration,
        evidence_refs=grounded.evidence,
    )
