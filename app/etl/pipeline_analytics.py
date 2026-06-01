"""Legacy placeholder-marketplace analytics payload builder (non-WB paths)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, cast
from uuid import UUID

from app.dto import TopSKUSummaryDTO
from app.dto.analytics_dto import AnomalyDTO
from app.etl.types import AnalyticsPayload
from app.models.report import Marketplace

if TYPE_CHECKING:
    import pandas as pd


class LegacyAnalyticsBuilder:
    """Deterministic AI DTO from observed dataframe context only."""

    @staticmethod
    def build_analytics_payload(
        *,
        report_id: UUID,
        report_created_at: datetime,
        marketplace: Marketplace,
        df: pd.DataFrame,
    ) -> AnalyticsPayload:
        from decimal import Decimal

        from app.domain.analytics import AnalyticsProcessor

        normalized_columns = {str(column).lower(): str(column) for column in df.columns}
        sku_column = LegacyAnalyticsBuilder._find_first_column(
            normalized_columns,
            ("internal_sku", "sku", "nm_id", "vendor_code", "offer_id", "артикул"),
        )
        revenue_column = LegacyAnalyticsBuilder._find_first_column(
            normalized_columns,
            ("revenue", "выручка", "sales_amount"),
        )
        profit_column = LegacyAnalyticsBuilder._find_first_column(
            normalized_columns,
            ("profit", "прибыль"),
        )
        date_column = LegacyAnalyticsBuilder._find_first_column(
            normalized_columns,
            ("report_date", "date", "period", "дата"),
        )
        anomalies: list[AnomalyDTO] = []

        def _anomaly(
            anomaly_type: str,
            *,
            severity: str = "medium",
            confidence: str = "0.95",
            message: str,
        ) -> AnomalyDTO:
            from decimal import Decimal as D

            return AnomalyDTO(
                type=anomaly_type,  # type: ignore[arg-type]
                severity=severity,  # type: ignore[arg-type]
                confidence=D(confidence),
                message=message,
            )

        if not sku_column:
            anomalies.append(
                _anomaly(
                    "missing_sku_column",
                    severity="high",
                    message="SKU column not found in uploaded report",
                )
            )
        if not revenue_column:
            anomalies.append(
                _anomaly(
                    "missing_total_revenue",
                    severity="high",
                    message="Revenue column not found in uploaded report",
                )
            )
        if not profit_column:
            anomalies.append(
                _anomaly(
                    "missing_total_profit",
                    severity="medium",
                    message="Profit column not found in uploaded report",
                )
            )

        sku_count = 0
        top_skus_summary: list[TopSKUSummaryDTO] = []
        if sku_column:
            sku_series = df[sku_column].dropna().astype(str).str.strip()
            sku_count = int(sku_series[sku_series != ""].nunique())
            for sku in sku_series[sku_series != ""].head(5).unique().tolist():
                top_skus_summary.append(
                    TopSKUSummaryDTO(
                        internal_sku=sku,
                        revenue=None,
                        profit=None,
                        units_sold=None,
                    )
                )

        total_revenue = LegacyAnalyticsBuilder._safe_sum_decimal(df, revenue_column)
        total_profit = LegacyAnalyticsBuilder._safe_sum_decimal(df, profit_column)
        margin = None
        if total_revenue is not None and total_revenue > 0 and total_profit is not None:
            margin = (total_profit / total_revenue) * Decimal("100")

        report_date = LegacyAnalyticsBuilder._extract_report_date(df, date_column)
        if report_date is None:
            report_date = report_created_at.date()
            anomalies.append(
                _anomaly(
                    "missing_report_date",
                    severity="low",
                    confidence="0.85",
                    message="Report date not found; using report creation date",
                )
            )

        insight = AnalyticsProcessor.prepare_ai_insight(
            report_id=report_id,
            report_date=report_date,
            marketplace_type=marketplace.value,
            sku_count=sku_count,
            total_revenue=total_revenue,
            total_profit=total_profit,
            margin=margin,
            top_skus_summary=top_skus_summary,
            anomalies=anomalies,
        )
        return cast(AnalyticsPayload, insight.to_legacy_dict())

    @staticmethod
    def _find_first_column(
        normalized_columns: dict[str, str],
        aliases: tuple[str, ...],
    ) -> str | None:
        for alias in aliases:
            for normalized, original in normalized_columns.items():
                if alias in normalized:
                    return original
        return None

    @staticmethod
    def _safe_sum_decimal(df: pd.DataFrame, column_name: str | None):
        from decimal import Decimal, InvalidOperation

        if not column_name:
            return None
        total = Decimal("0")
        has_value = False
        for value in df[column_name].dropna():
            try:
                total += Decimal(str(value).replace(",", ".").strip())
                has_value = True
            except (InvalidOperation, AttributeError):
                continue
        return total if has_value else None

    @staticmethod
    def _extract_report_date(df: pd.DataFrame, column_name: str | None):
        if not column_name:
            return None
        values = df[column_name].dropna()
        if values.empty:
            return None
        parsed = values.astype("datetime64[ns]", errors="ignore")
        first_value = parsed.iloc[0]
        if hasattr(first_value, "date"):
            return first_value.date()
        return None
