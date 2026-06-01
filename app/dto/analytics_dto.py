from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TopSKUSummaryDTO(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    internal_sku: str = Field(min_length=1, max_length=128)
    revenue: Decimal | None = Field(default=None, ge=0)
    profit: Decimal | None = Field(default=None, ge=0)
    units_sold: int | None = Field(default=None, ge=0)


AnomalyType = Literal[
    "missing_sku_column",
    "missing_total_revenue",
    "missing_total_profit",
    "missing_report_date",
    "data_quality",
    "schema_mismatch",
]

AnomalySeverity = Literal["low", "medium", "high"]


class AnomalyDTO(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    type: AnomalyType
    severity: AnomalySeverity
    confidence: Decimal = Field(ge=0, le=1)
    message: str = Field(min_length=1, max_length=512)


class ContextDTO(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    report_id: UUID
    report_date: date
    marketplace_type: str = Field(min_length=1, max_length=32)


class MetricsDTO(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True)

    sku_count: int = Field(ge=0)
    total_revenue: Decimal | None = Field(default=None, ge=0)
    total_profit: Decimal | None = Field(default=None, ge=0)
    margin: Decimal | None = None
    top_skus_summary: list[TopSKUSummaryDTO] = Field(default_factory=list)


class AIInsightInputDTO(BaseModel):
    """Normalized AI contract composed from focused sub-DTOs."""

    model_config = ConfigDict(strict=True, frozen=True)

    context: ContextDTO
    metrics: MetricsDTO
    anomalies: list[AnomalyDTO] = Field(default_factory=list, max_length=50)

    def to_legacy_dict(self) -> dict:
        """Backward-compatible flat payload for ai_insights.context_payload."""
        flat = {
            "report_id": str(self.context.report_id),
            "report_date": self.context.report_date.isoformat(),
            "marketplace_type": self.context.marketplace_type,
            "sku_count": self.metrics.sku_count,
            "total_revenue": (
                str(self.metrics.total_revenue) if self.metrics.total_revenue is not None else None
            ),
            "total_profit": (
                str(self.metrics.total_profit) if self.metrics.total_profit is not None else None
            ),
            "margin": str(self.metrics.margin) if self.metrics.margin is not None else None,
            "top_skus_summary": [
                item.model_dump(mode="json") for item in self.metrics.top_skus_summary
            ],
            "anomalies": [item.model_dump(mode="json") for item in self.anomalies],
        }
        return flat


class AIInputDTO(BaseModel):
    """
    Legacy flat AI input contract (kept for pipeline compatibility).
    Prefer AIInsightInputDTO for new code paths.
    """

    model_config = ConfigDict(strict=True, frozen=True)

    report_id: UUID
    report_date: date
    marketplace_type: str = Field(min_length=1, max_length=32)
    sku_count: int = Field(ge=0)
    total_revenue: Decimal | None = Field(default=None, ge=0)
    total_profit: Decimal | None = Field(default=None, ge=0)
    margin: Decimal | None = None
    top_skus_summary: list[TopSKUSummaryDTO] = Field(default_factory=list)
    anomalies: list[AnomalyDTO] = Field(default_factory=list, max_length=50)

    @classmethod
    def from_insight(cls, insight: AIInsightInputDTO) -> "AIInputDTO":
        return cls(
            report_id=insight.context.report_id,
            report_date=insight.context.report_date,
            marketplace_type=insight.context.marketplace_type,
            sku_count=insight.metrics.sku_count,
            total_revenue=insight.metrics.total_revenue,
            total_profit=insight.metrics.total_profit,
            margin=insight.metrics.margin,
            top_skus_summary=insight.metrics.top_skus_summary,
            anomalies=insight.anomalies,
        )
