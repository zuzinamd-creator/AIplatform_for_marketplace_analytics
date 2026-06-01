from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.core.observability.etl_metrics import bind_log_context, record_metrics
from app.domain.analytics import AnalyticsProcessor
from app.domain.analytics.aggregation import AggregationEngine
from app.domain.data_quality.validator import DataQualityValidator
from app.domain.finance.ledger import LedgerBuilder
from app.domain.finance.types import SkuCostSnapshot
from app.domain.inventory.analytics_payload import extend_analytics_payload
from app.domain.inventory.ledger_row import InventoryLedgerRow
from app.domain.inventory.movements import InventoryMovementBuilder
from app.domain.inventory.pipeline import InventorySnapshotPipeline
from app.domain.reconciliation.calculator import ReconciliationCalculator
from app.domain.semantics.governance_policy import assert_ingest_allowed
from app.dto import TopSKUSummaryDTO
from app.etl.anomaly_buffer import EtlAnomalyBuffer
from app.etl.loaders import dataframe_to_raw_records, load_file_to_dataframe
from app.etl.wb.types import WbFinancialProcessResult
from app.models.report import Marketplace
from app.parsers.wb import parse_wb_report
from app.parsers.wb.semantics import SEMANTICS_VERSION


class WbFinancialProcessor:
    """
    CPU-only WB financial pipeline:
    parser -> normalization -> ledger -> aggregates -> analytics DTO
    """

    @staticmethod
    def process(
        *,
        report_id: UUID,
        report_created_at: datetime,
        filename: str,
        content: bytes,
        costs_by_sku: dict[str, list[SkuCostSnapshot]] | None = None,
    ) -> WbFinancialProcessResult:
        bind_log_context(
            operation_stage="parse",
            semantics_version=SEMANTICS_VERSION,
        )
        assert_ingest_allowed(SEMANTICS_VERSION)
        anomaly_buffer = EtlAnomalyBuffer()

        df = load_file_to_dataframe(filename, content)
        parser, normalized_rows = parse_wb_report(df)
        default_date = report_created_at.date()
        ledger_entries = LedgerBuilder.from_normalized_rows(
            normalized_rows,
            default_date=default_date,
        )
        inventory_movements = InventoryMovementBuilder.from_normalized_rows(
            normalized_rows,
            default_date=default_date,
            costs_by_sku=costs_by_sku,
        )
        reconciliation = ReconciliationCalculator.calculate(ledger_entries)
        daily, sku_metrics = AggregationEngine.build(
            ledger_entries,
            marketplace=Marketplace.WILDBERRIES,
            costs_by_sku=costs_by_sku or {},
            default_date=default_date,
        )

        total_revenue = reconciliation.gross_revenue
        total_profit = sum((d.net_profit for d in daily), start=Decimal("0"))
        margin = (
            (total_profit / total_revenue * Decimal("100"))
            if total_revenue > Decimal("0")
            else None
        )
        top_skus = [
            TopSKUSummaryDTO(
                internal_sku=item.sku,
                revenue=item.revenue,
                profit=item.net_profit,
                units_sold=item.units_sold,
            )
            for item in sorted(sku_metrics, key=lambda row: row.revenue, reverse=True)[:5]
        ]
        insight = AnalyticsProcessor.prepare_ai_insight(
            report_id=report_id,
            report_date=default_date,
            marketplace_type=Marketplace.WILDBERRIES.value,
            sku_count=len({row.sku for row in normalized_rows if row.sku}),
            total_revenue=total_revenue,
            total_profit=total_profit,
            margin=margin,
            top_skus_summary=top_skus,
            anomalies=[],
        )
        ledger_rows = [InventoryLedgerRow.from_draft(item) for item in inventory_movements]
        _, loss_analytics = InventorySnapshotPipeline.rebuild(
            ledger_rows,
            costs_by_sku=costs_by_sku or {},
        )
        analytics_payload = extend_analytics_payload(
            insight.to_legacy_dict(),
            loss_analytics=loss_analytics,
        )

        anomaly_buffer.extend(
            DataQualityValidator.validate_wb_process(
                report_id=report_id,
                source_file_name=filename,
                inventory_movements=inventory_movements,
                today=default_date,
            )
        )
        rows_rejected = len(anomaly_buffer)
        record_metrics(
            rows_processed=len(normalized_rows),
            rows_rejected=rows_rejected,
        )

        raw_snapshot = dataframe_to_raw_records(df)
        return WbFinancialProcessResult(
            report_id=report_id,
            parser_name=parser.name,
            parser_version=parser.version,
            raw_snapshot=raw_snapshot,  # type: ignore[arg-type]
            normalized_rows=normalized_rows,
            ledger_entries=ledger_entries,
            inventory_movements=inventory_movements,
            reconciliation=reconciliation,
            daily_aggregates=daily,
            sku_daily_metrics=sku_metrics,
            analytics_payload=analytics_payload,  # type: ignore[arg-type]
            default_date=default_date,
            row_count=int(raw_snapshot["row_count"]),
            etl_anomalies=tuple(anomaly_buffer.peek()),
        )

    @staticmethod
    def enrich_with_costs(
        result: WbFinancialProcessResult,
        costs_by_sku: dict[str, list[SkuCostSnapshot]],
    ) -> WbFinancialProcessResult:
        daily, sku_metrics = AggregationEngine.build(
            result.ledger_entries,
            marketplace=Marketplace.WILDBERRIES,
            costs_by_sku=costs_by_sku,
            default_date=result.default_date,
        )
        inventory_movements = InventoryMovementBuilder.from_normalized_rows(
            result.normalized_rows,
            default_date=result.default_date,
            costs_by_sku=costs_by_sku,
        )
        total_revenue = result.reconciliation.gross_revenue
        total_profit = sum((d.net_profit for d in daily), start=Decimal("0"))
        margin = (
            (total_profit / total_revenue * Decimal("100"))
            if total_revenue > Decimal("0")
            else None
        )
        top_skus = [
            TopSKUSummaryDTO(
                internal_sku=item.sku,
                revenue=item.revenue,
                profit=item.net_profit,
                units_sold=item.units_sold,
            )
            for item in sorted(sku_metrics, key=lambda row: row.revenue, reverse=True)[:5]
        ]
        insight = AnalyticsProcessor.prepare_ai_insight(
            report_id=result.report_id,
            report_date=result.default_date,
            marketplace_type=Marketplace.WILDBERRIES.value,
            sku_count=len({row.sku for row in result.normalized_rows if row.sku}),
            total_revenue=total_revenue,
            total_profit=total_profit,
            margin=margin,
            top_skus_summary=top_skus,
            anomalies=[],
        )
        ledger_rows = [InventoryLedgerRow.from_draft(item) for item in inventory_movements]
        _, loss_analytics = InventorySnapshotPipeline.rebuild(ledger_rows, costs_by_sku=costs_by_sku)
        analytics_payload = extend_analytics_payload(
            insight.to_legacy_dict(),
            loss_analytics=loss_analytics,
        )
        return WbFinancialProcessResult(
            report_id=result.report_id,
            parser_name=result.parser_name,
            parser_version=result.parser_version,
            raw_snapshot=result.raw_snapshot,
            normalized_rows=result.normalized_rows,
            ledger_entries=result.ledger_entries,
            inventory_movements=inventory_movements,
            reconciliation=result.reconciliation,
            daily_aggregates=daily,
            sku_daily_metrics=sku_metrics,
            analytics_payload=analytics_payload,  # type: ignore[arg-type]
            default_date=result.default_date,
            row_count=result.row_count,
            etl_anomalies=result.etl_anomalies,
        )
