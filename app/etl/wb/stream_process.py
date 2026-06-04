"""Streamed WB CPU parse — yields chunks without holding all normalized rows."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from uuid import UUID

from app.core.observability.etl_metrics import bind_log_context
from app.etl.worker_shutdown import ShutdownCheck, WorkerShutdownRequested, is_shutdown
from app.domain.data_quality.validator import DataQualityValidator
from app.domain.finance.ledger import LedgerBuilder
from app.domain.finance.types import SkuCostSnapshot
from app.domain.inventory.movements import InventoryMovementBuilder
from app.domain.reconciliation.calculator import ReconciliationCalculator
from app.domain.semantics.governance_policy import assert_ingest_allowed
from app.etl.anomaly_buffer import EtlAnomalyBuffer
from app.etl.wb.processor import PROCESS_CHUNK_SIZE
from app.etl.wb.stream_types import WbProcessChunk
from app.parsers.wb.semantics import SEMANTICS_VERSION
from app.parsers.wb.streaming import iter_wb_normalized_rows


class WbStreamChunkIterator:
    """Iterable parse session: DQ anomalies and parser metadata available after iteration."""

    def __init__(
        self,
        *,
        report_id: UUID,
        report_created_at: datetime,
        path: Path,
        filename: str,
        costs_by_sku: dict[str, list[SkuCostSnapshot]] | None = None,
        shutdown_check: ShutdownCheck | None = None,
    ) -> None:
        self.report_id = report_id
        self.report_created_at = report_created_at
        self.path = path
        self.filename = filename
        self.costs_by_sku = costs_by_sku
        self.shutdown_check = shutdown_check
        self.anomaly_buffer = EtlAnomalyBuffer()
        self.parser_name = ""
        self.parser_version = ""
        self.chunks_completed = 0

    def __iter__(self) -> Iterator[WbProcessChunk]:
        bind_log_context(operation_stage="parse_stream", semantics_version=SEMANTICS_VERSION)
        assert_ingest_allowed(SEMANTICS_VERSION)
        costs = self.costs_by_sku or {}
        default_date = self.report_created_at.date()
        seen_keys: dict[tuple[str, str, str, str], int] = defaultdict(int)
        parser_seen = False

        for active_parser, normalized_chunk in iter_wb_normalized_rows(
            self.path,
            filename=self.filename,
            chunk_size=PROCESS_CHUNK_SIZE,
        ):
            if is_shutdown(self.shutdown_check):
                raise WorkerShutdownRequested(
                    phase="parse",
                    chunks_completed=self.chunks_completed,
                )
            self.parser_name = active_parser.name
            self.parser_version = active_parser.version
            parser_seen = True
            chunk_ledger = LedgerBuilder.from_normalized_rows(
                normalized_chunk,
                default_date=default_date,
            )
            chunk_inventory = InventoryMovementBuilder.from_normalized_rows(
                normalized_chunk,
                default_date=default_date,
                costs_by_sku=costs,
            )
            partial = ReconciliationCalculator.calculate(chunk_ledger)
            self.anomaly_buffer.extend(
                DataQualityValidator.validate_wb_process(
                    report_id=self.report_id,
                    source_file_name=self.filename,
                    inventory_movements=chunk_inventory,
                    today=default_date,
                    seen_keys=seen_keys,
                )
            )
            yield WbProcessChunk(
                parser_name=self.parser_name,
                parser_version=self.parser_version,
                normalized_rows=normalized_chunk,
                ledger_entries=chunk_ledger,
                inventory_movements=chunk_inventory,
                reconciliation=partial,
            )
            self.chunks_completed += 1

        if not parser_seen:
            raise ValueError("Report file contains no data rows")
