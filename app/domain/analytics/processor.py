from datetime import date
from decimal import Decimal

from app.dto.analytics_dto import (
    AIInputDTO,
    AIInsightInputDTO,
    AnomalyDTO,
    ContextDTO,
    MetricsDTO,
    TopSKUSummaryDTO,
)


class AnalyticsProcessor:
    """
    Domain logic for processing analytics datasets and preparing
    structured packages for downstream consumption (e.g. by AI/ML layers).
    """

    @staticmethod
    def prepare_ai_insight(
        *,
        report_id,
        report_date: date,
        marketplace_type: str,
        sku_count: int,
        total_revenue: Decimal | None,
        total_profit: Decimal | None,
        margin: Decimal | None,
        top_skus_summary: list[TopSKUSummaryDTO],
        anomalies: list[AnomalyDTO],
    ) -> AIInsightInputDTO:
        return AIInsightInputDTO(
            context=ContextDTO(
                report_id=report_id,
                report_date=report_date,
                marketplace_type=marketplace_type,
            ),
            metrics=MetricsDTO(
                sku_count=sku_count,
                total_revenue=total_revenue,
                total_profit=total_profit,
                margin=margin,
                top_skus_summary=top_skus_summary,
            ),
            anomalies=anomalies,
        )

    @staticmethod
    def prepare_ai_context(
        *,
        report_id,
        report_date: date,
        marketplace_type: str,
        sku_count: int,
        total_revenue: Decimal | None,
        total_profit: Decimal | None,
        margin: Decimal | None,
        top_skus_summary: list[TopSKUSummaryDTO],
        anomalies: list[AnomalyDTO],
    ) -> AIInputDTO:
        """Backward-compatible flat DTO wrapper."""
        insight = AnalyticsProcessor.prepare_ai_insight(
            report_id=report_id,
            report_date=report_date,
            marketplace_type=marketplace_type,
            sku_count=sku_count,
            total_revenue=total_revenue,
            total_profit=total_profit,
            margin=margin,
            top_skus_summary=top_skus_summary,
            anomalies=anomalies,
        )
        return AIInputDTO.from_insight(insight)
