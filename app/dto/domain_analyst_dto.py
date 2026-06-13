"""Domain analyst and executive intelligence DTOs (governed inputs only)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.dto.ai_analytics_dto import EvidenceRefDTO, GroundedContextDTO
from app.dto.analytics_dto import AIInsightInputDTO, AnomalyDTO, TopSKUSummaryDTO

SeverityLevel = Literal["low", "medium", "high", "critical"]


class DomainAnalystId(StrEnum):
    SALES = "sales_analyst"
    ADS = "ads_analyst"
    FUNNEL = "funnel_analyst"
    INVENTORY = "inventory_analyst"
    MARKETPLACE_COMPARISON = "marketplace_comparison_analyst"
    ANOMALY = "anomaly_analyst"
    LOGISTICS = "logistics_analyst"
    RETURNS = "returns_analyst"
    REVENUE_CHANGE = "revenue_change_analyst"
    CONCENTRATION = "concentration_analyst"


class SalesAnalyticsSlice(BaseModel):
    """Pre-computed sales KPIs from deterministic layer (read-only for AI)."""

    model_config = ConfigDict(strict=True, frozen=True)

    sku_count: int = 0
    total_revenue: Decimal | None = None
    total_profit: Decimal | None = None
    margin: Decimal | None = None
    top_skus: tuple[TopSKUSummaryDTO, ...] = ()


class AdsAnalyticsSlice(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    marketplace_type: str = ""
    ad_spend_available: bool = False
    notes: str = ""


class FunnelAnalyticsSlice(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    sku_count: int = 0
    top_sku_concentration: Decimal | None = None


class InventorySkuRow(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    sku: str
    stock_units: int = 0
    frozen_capital: Decimal | None = None
    days_since_last_sale: int | None = None
    share_pct: Decimal = Decimal("0")


class InventoryAnalyticsSlice(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    sku_count: int = 0
    total_skus: int = 0
    inventory_signals_available: bool = False
    turnover_available: bool = False
    frozen_capital_available: bool = False
    total_frozen_capital: Decimal | None = None
    frozen_capital_share_pct: Decimal | None = None
    slow_mover_count: int = 0
    dead_stock_count: int = 0
    overstock_count: int = 0
    stock_concentration_top3_pct: Decimal | None = None
    inventory_risk_level: str = "low"
    top_slow_movers: tuple[InventorySkuRow, ...] = ()
    top_dead_stock: tuple[InventorySkuRow, ...] = ()
    top_frozen_capital_skus: tuple[InventorySkuRow, ...] = ()


class MarketplaceComparisonSlice(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    marketplace_type: str = ""
    single_marketplace_report: bool = True


class AnomalyAnalyticsSlice(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    anomalies: tuple[AnomalyDTO, ...] = ()


class SkuSignalDTO(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    sku: str
    share_pct: Decimal = Decimal("0")
    amount: Decimal = Decimal("0")


class LogisticsAnalyticsSlice(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    logistics_share_pct: Decimal | None = None
    logistics_share_delta_pp: Decimal | None = None
    high_burden_skus: tuple[SkuSignalDTO, ...] = ()


class ReturnsAnalyticsSlice(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    return_rate_pct: Decimal | None = None
    return_rate_delta_pp: Decimal | None = None
    top_return_skus: tuple[SkuSignalDTO, ...] = ()


class RevenueChangeAnalyticsSlice(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    revenue_change_pct: Decimal | None = None
    profit_change_pct: Decimal | None = None
    compare_available: bool = False
    sku_revenue_drivers: tuple[SkuSignalDTO, ...] = ()


class ConcentrationAnalyticsSlice(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    top1_share_pct: Decimal | None = None
    top3_share_pct: Decimal | None = None
    top_skus: tuple[str, ...] = ()


class AnalyticalIntelligencePackage(BaseModel):
    """Governed analytical package — AI reasons over slices, never computes KPIs."""

    model_config = ConfigDict(strict=True, frozen=True)

    semantics_version: str
    data_as_of: datetime
    report_id: UUID | None = None
    grounded: GroundedContextDTO
    insight: AIInsightInputDTO | None = None
    sales: SalesAnalyticsSlice = Field(default_factory=SalesAnalyticsSlice)
    ads: AdsAnalyticsSlice = Field(default_factory=AdsAnalyticsSlice)
    funnel: FunnelAnalyticsSlice = Field(default_factory=FunnelAnalyticsSlice)
    inventory: InventoryAnalyticsSlice = Field(default_factory=InventoryAnalyticsSlice)
    marketplace: MarketplaceComparisonSlice = Field(default_factory=MarketplaceComparisonSlice)
    anomaly: AnomalyAnalyticsSlice = Field(default_factory=AnomalyAnalyticsSlice)
    logistics: LogisticsAnalyticsSlice = Field(default_factory=LogisticsAnalyticsSlice)
    returns: ReturnsAnalyticsSlice = Field(default_factory=ReturnsAnalyticsSlice)
    revenue_change: RevenueChangeAnalyticsSlice = Field(default_factory=RevenueChangeAnalyticsSlice)
    concentration: ConcentrationAnalyticsSlice = Field(default_factory=ConcentrationAnalyticsSlice)
    evidence_refs: tuple[EvidenceRefDTO, ...] = ()


class DomainFindingDTO(BaseModel):
    model_config = ConfigDict(strict=True)

    finding_id: str
    statement: str = Field(min_length=1, max_length=512)
    confidence: Decimal = Field(ge=0, le=1)
    severity: SeverityLevel
    evidence_refs: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list, max_length=10)


class DomainAnalystOutputDTO(BaseModel):
    model_config = ConfigDict(strict=True)

    analyst_id: DomainAnalystId
    contract_version: str
    findings: list[DomainFindingDTO] = Field(default_factory=list, max_length=20)
    overall_confidence: Decimal = Field(ge=0, le=1)
    advisory_only: bool = True
    insufficient_data: bool = False


class ConflictResolutionNoteDTO(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    conflict_id: str
    analysts_involved: tuple[str, ...]
    resolution: str
    retained_finding_id: str | None = None
    suppressed_finding_id: str | None = None


class ExecutiveInsightDTO(BaseModel):
    """Seller-facing insight after executive aggregation."""

    model_config = ConfigDict(strict=True)

    insight_id: str
    analyst_id: str
    analyst_label: str
    statement: str
    confidence: Decimal = Field(ge=0, le=1)
    severity: SeverityLevel
    priority_rank: int = Field(ge=1)
    evidence_refs: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    business_impact_score: Decimal = Field(ge=0, le=100, default=Decimal("0"))
    reasoning_summary: str = ""


class ExecutiveAggregationResultDTO(BaseModel):
    model_config = ConfigDict(strict=True)

    narrative: str
    executive_summary: str
    prioritized_insights: list[ExecutiveInsightDTO] = Field(default_factory=list, max_length=30)
    final_recommendations: list[str] = Field(default_factory=list, max_length=15)
    overall_confidence: Decimal = Field(ge=0, le=1)
    business_impact_estimate: str = ""
    conflicts_resolved: list[ConflictResolutionNoteDTO] = Field(default_factory=list)
    confidence_propagation: dict[str, str] = Field(default_factory=dict)
    domain_outputs: list[DomainAnalystOutputDTO] = Field(default_factory=list)
    aggregation_notes: list[str] = Field(default_factory=list)


class MultiLayerReasoningTraceDTO(BaseModel):
    model_config = ConfigDict(strict=True)

    architecture_version: str = "2.0"
    domain_outputs: list[DomainAnalystOutputDTO] = Field(default_factory=list)
    executive: ExecutiveAggregationResultDTO | None = None
    conflict_resolution: list[ConflictResolutionNoteDTO] = Field(default_factory=list)
    confidence_propagation: dict[str, str] = Field(default_factory=dict)
    domain_insights: list[ExecutiveInsightDTO] = Field(default_factory=list)
