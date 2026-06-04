from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import TypeVar
from uuid import UUID

from app.core.observability.etl_metrics import bind_log_context, record_metrics
from app.domain.analytics import AnalyticsProcessor
from app.domain.analytics.aggregation import AggregationEngine
from app.domain.data_quality.validator import DataQualityValidator
from app.domain.etl.anomaly_draft import EtlAnomalyDraft
from app.domain.finance.ledger import LedgerBuilder
from app.domain.finance.types import LedgerEntryDraft, SkuCostSnapshot
from app.domain.inventory.analytics_payload import extend_analytics_payload
from app.domain.inventory.ledger_row import InventoryLedgerRow
from app.domain.inventory.movements import InventoryMovementBuilder
from app.domain.inventory.pipeline import InventorySnapshotPipeline
from app.domain.inventory.types import InventoryMovementDraft
from app.domain.reconciliation.calculator import ReconciliationCalculator, ReconciliationResult
from app.domain.semantics.governance_policy import assert_ingest_allowed
from app.dto import TopSKUSummaryDTO
from app.etl.anomaly_buffer import EtlAnomalyBuffer
from app.etl.loaders import load_file_to_dataframe
from app.etl.types import RawDataSnapshot
from app.domain.inventory.opening_balance import is_opening_balance_movement
from app.etl.wb.stream_types import WbProcessChunk
from app.etl.wb.types import WbFinancialProcessResult
from app.models.report import Marketplace
from app.parsers.wb import parse_wb_report
from app.parsers.wb.base import NormalizedWbRow
from app.parsers.wb.semantics import SEMANTICS_VERSION

# CPU chunk size: limits peak working set while building ledger/inventory lists.
PROCESS_CHUNK_SIZE = 1000
RAW_SNAPSHOT_SAMPLE_ROWS = 5000

T = TypeVar("T")


def _iter_chunks(items: Sequence[T], *, chunk_size: int = PROCESS_CHUNK_SIZE) -> Iterator[list[T]]:
    if not items:
        return
    for offset in range(0, len(items), chunk_size):
        yield list(items[offset : offset + chunk_size])


def _raw_snapshot_from_normalized_rows(
    normalized_rows: list[NormalizedWbRow],
    *,
    max_sample: int = RAW_SNAPSHOT_SAMPLE_ROWS,
) -> RawDataSnapshot:
    """Lightweight raw snapshot without keeping the full pandas DataFrame in memory."""
    sample = normalized_rows[:max_sample]
    columns: list[str] = []
    if sample and sample[0].raw:
        columns = sorted({str(k) for k in sample[0].raw.keys()})
    sample_rows = [
        {str(k): "" if v is None else str(v) for k, v in row.raw.items()} for row in sample
    ]
    return {
        "columns": columns,
        "row_count": len(normalized_rows),
        "sample_rows": sample_rows,
    }


def _merge_reconciliation(
    left: ReconciliationResult,
    right: ReconciliationResult,
) -> ReconciliationResult:
    """Combine two partial reconciliation passes (additive semantics)."""
    gross = left.gross_revenue + right.gross_revenue
    commissions = left.wb_commissions + right.wb_commissions
    logistics = left.logistics + right.logistics
    deductions = left.deductions + right.deductions
    returns_amount = left.returns_amount + right.returns_amount
    payout_actual = left.actual_payout + right.actual_payout
    net = gross - commissions - logistics - deductions - returns_amount
    expected = net
    difference = payout_actual - expected
    return ReconciliationResult(
        gross_revenue=gross,
        net_revenue=net,
        wb_commissions=commissions,
        logistics=logistics,
        deductions=deductions,
        returns_amount=returns_amount,
        expected_payout=expected,
        actual_payout=payout_actual,
        difference=difference,
    )


class WbFinancialProcessor:
    """
    CPU-only WB financial pipeline:
    parser -> normalization -> ledger -> aggregates -> analytics DTO

    Large files are processed in fixed-size chunks to reduce peak RAM.
    Supabase I/O is handled in worker (read) and WbFinancialPersistService (write).
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
        costs = costs_by_sku or {}

        df = load_file_to_dataframe(filename, content)
        parser, normalized_rows = parse_wb_report(df)
        del df

        default_date = report_created_at.date()
        ledger_entries: list[LedgerEntryDraft] = []
        inventory_movements: list[InventoryMovementDraft] = []
        reconciliation: ReconciliationResult | None = None

        for chunk in _iter_chunks(normalized_rows):
            chunk_ledger = LedgerBuilder.from_normalized_rows(chunk, default_date=default_date)
            ledger_entries.extend(chunk_ledger)
            inventory_movements.extend(
                InventoryMovementBuilder.from_normalized_rows(
                    chunk,
                    default_date=default_date,
                    costs_by_sku=costs,
                )
            )
            partial = ReconciliationCalculator.calculate(chunk_ledger)
            reconciliation = (
                partial if reconciliation is None else _merge_reconciliation(reconciliation, partial)
            )

        if reconciliation is None:
            reconciliation = ReconciliationCalculator.calculate([])

        daily, sku_metrics = AggregationEngine.build(
            ledger_entries,
            marketplace=Marketplace.WILDBERRIES,
            costs_by_sku=costs,
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
            costs_by_sku=costs,
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
        record_metrics(
            rows_processed=len(normalized_rows),
            rows_rejected=len(anomaly_buffer),
        )

        raw_snapshot = _raw_snapshot_from_normalized_rows(normalized_rows)
        return WbFinancialProcessResult(
            report_id=report_id,
            parser_name=parser.name,
            parser_version=parser.version,
            raw_snapshot=raw_snapshot,
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
    def build_streamed_result(
        *,
        report_id: UUID,
        parser_name: str,
        parser_version: str,
        filename: str,
        default_date: date,
        row_count: int,
        reconciliation: ReconciliationResult,
        raw_snapshot: RawDataSnapshot,
        etl_anomalies: tuple[EtlAnomalyDraft, ...] = (),
        earliest_movement_date: date | None = None,
        sku_count: int = 0,
    ) -> WbFinancialProcessResult:
        """Finalize CPU result after phase-1 chunks were persisted (lists intentionally empty)."""
        total_revenue = reconciliation.gross_revenue
        insight = AnalyticsProcessor.prepare_ai_insight(
            report_id=report_id,
            report_date=default_date,
            marketplace_type=Marketplace.WILDBERRIES.value,
            sku_count=sku_count,
            total_revenue=total_revenue,
            total_profit=Decimal("0"),
            margin=None,
            top_skus_summary=[],
            anomalies=[],
        )
        analytics_payload = extend_analytics_payload(
            insight.to_legacy_dict(),
            loss_analytics=None,
        )
        return WbFinancialProcessResult(
            report_id=report_id,
            parser_name=parser_name,
            parser_version=parser_version,
            raw_snapshot=raw_snapshot,
            normalized_rows=[],
            ledger_entries=[],
            inventory_movements=[],
            reconciliation=reconciliation,
            daily_aggregates=[],
            sku_daily_metrics=[],
            analytics_payload=analytics_payload,  # type: ignore[arg-type]
            default_date=default_date,
            row_count=row_count,
            etl_anomalies=etl_anomalies,
            streamed=True,
            earliest_movement_date=earliest_movement_date,
        )

    @staticmethod
    def merge_stream_state(
        *,
        reconciliation: ReconciliationResult | None,
        chunk: WbProcessChunk,
        opening_movements: list[InventoryMovementDraft],
        batch_first_dates: dict[tuple[str | None, str | None], date],
        earliest_movement_date: date | None,
        sample_rows: list[dict[str, str]],
        columns: set[str],
        sku_ids: set[str],
        max_sample: int = RAW_SNAPSHOT_SAMPLE_ROWS,
    ) -> tuple[ReconciliationResult | None, date | None]:
        for movement in chunk.inventory_movements:
            if is_opening_balance_movement(movement.canonical_payload):
                opening_movements.append(movement)
            elif movement.sku:
                key = (movement.sku, movement.warehouse_name)
                existing = batch_first_dates.get(key)
                if existing is None or movement.operation_date < existing:
                    batch_first_dates[key] = movement.operation_date
            if earliest_movement_date is None or movement.operation_date < earliest_movement_date:
                earliest_movement_date = movement.operation_date

        for row in chunk.normalized_rows:
            if row.sku:
                sku_ids.add(row.sku)
            if len(sample_rows) < max_sample:
                columns.update(str(k) for k in row.raw.keys())
                sample_rows.append(
                    {str(k): "" if v is None else str(v) for k, v in row.raw.items()}
                )

        reconciliation = (
            chunk.reconciliation
            if reconciliation is None
            else _merge_reconciliation(reconciliation, chunk.reconciliation)
        )
        return reconciliation, earliest_movement_date

    @staticmethod
    def enrich_with_costs(
        result: WbFinancialProcessResult,
        costs_by_sku: dict[str, list[SkuCostSnapshot]],
    ) -> WbFinancialProcessResult:
        if result.streamed:
            return result
        daily, sku_metrics = AggregationEngine.build(
            result.ledger_entries,
            marketplace=Marketplace.WILDBERRIES,
            costs_by_sku=costs_by_sku,
            default_date=result.default_date,
        )
        inventory_movements: list[InventoryMovementDraft] = []
        for chunk in _iter_chunks(result.normalized_rows):
            inventory_movements.extend(
                InventoryMovementBuilder.from_normalized_rows(
                    chunk,
                    default_date=result.default_date,
                    costs_by_sku=costs_by_sku,
                )
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
