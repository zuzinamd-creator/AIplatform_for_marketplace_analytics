"""Worker-side streamed WB parse + phase-1 persist."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.observability import get_logger
from app.core.observability.etl_metrics import record_metrics
from app.etl.worker_shutdown import ShutdownCheck, WorkerShutdownRequested, is_shutdown
from app.domain.finance.types import SkuCostSnapshot
from app.domain.inventory.types import InventoryMovementDraft
from app.domain.reconciliation.calculator import ReconciliationCalculator
from app.etl.types import ETLResult
from app.etl.wb.persist import WbFinancialPersistService
from app.etl.wb.processor import RAW_SNAPSHOT_SAMPLE_ROWS, WbFinancialProcessor
from app.etl.wb.stream_process import WbStreamChunkIterator
from app.etl.wb.types import WbFinancialProcessResult
from app.models.report import Report

logger = get_logger("wb_stream_pipeline")


async def process_wb_streamed(
    *,
    db: AsyncSession,
    user_id: UUID,
    report: Report,
    path: Path,
    filename: str,
    job_id: UUID | None = None,
    shutdown_check: ShutdownCheck | None = None,
) -> ETLResult:
    """
    Parse from disk, persist phase-1 per chunk, return slim ETLResult for phases 2–3.
    """
    persist_service = WbFinancialPersistService(db, user_id)
    costs = await persist_service.load_cost_snapshots(db, user_id)

    parse_session = WbStreamChunkIterator(
        report_id=report.id,
        report_created_at=report.created_at,
        path=path,
        filename=filename,
        costs_by_sku=costs,
        shutdown_check=shutdown_check,
    )

    reconciliation = None
    row_count = 0
    opening_movements: list[InventoryMovementDraft] = []
    batch_first_dates: dict[tuple[str | None, str | None], date] = {}
    earliest_movement_date: date | None = None
    sample_rows: list[dict[str, str]] = []
    columns: set[str] = set()
    sku_ids: set[str] = set()
    chunks_persisted = 0
    try:
        for chunk in parse_session:
            row_count += len(chunk.normalized_rows)
            reconciliation, earliest_movement_date = WbFinancialProcessor.merge_stream_state(
                reconciliation=reconciliation,
                chunk=chunk,
                opening_movements=opening_movements,
                batch_first_dates=batch_first_dates,
                earliest_movement_date=earliest_movement_date,
                sample_rows=sample_rows,
                columns=columns,
                sku_ids=sku_ids,
                max_sample=RAW_SNAPSHOT_SAMPLE_ROWS,
            )
            await persist_service.persist_phase1_chunk(
                report=report,
                chunk=chunk,
                job_id=job_id,
            )
            chunks_persisted += 1
            if is_shutdown(shutdown_check):
                logger.info(
                    "wb_stream_graceful_stop",
                    extra={
                        "job_id": str(job_id) if job_id else None,
                        "report_id": str(report.id),
                        "chunks_persisted": chunks_persisted,
                    },
                )
                raise WorkerShutdownRequested(
                    phase="persist_phase1",
                    chunks_completed=chunks_persisted,
                )
    except WorkerShutdownRequested:
        raise
    except Exception:
        await persist_service.rollback_pending()
        raise

    if reconciliation is None:
        reconciliation = ReconciliationCalculator.calculate([])

    record_metrics(
        rows_processed=row_count,
        rows_rejected=len(parse_session.anomaly_buffer),
    )

    raw_snapshot = {
        "columns": sorted(columns),
        "row_count": row_count,
        "sample_rows": sample_rows,
    }
    wb_result = WbFinancialProcessor.build_streamed_result(
        report_id=report.id,
        parser_name=parse_session.parser_name,
        parser_version=parse_session.parser_version,
        filename=filename,
        default_date=report.created_at.date(),
        row_count=row_count,
        reconciliation=reconciliation,
        raw_snapshot=raw_snapshot,  # type: ignore[arg-type]
        etl_anomalies=tuple(parse_session.anomaly_buffer.peek()),
        earliest_movement_date=earliest_movement_date,
        sku_count=len(sku_ids),
    )
    await persist_service.persist_raw_report_row(
        report=report,
        file_checksum=report.file_checksum or "",
        storage_uri=report.file_path or "",
        result=wb_result,
        job_id=job_id,
    )

    return ETLResult(
        raw_data=wb_result.raw_snapshot,
        row_count=wb_result.row_count,
        analytics_payload=wb_result.analytics_payload,
        wb_financial=wb_result,
        wb_opening_movements=opening_movements,
        wb_batch_first_dates=batch_first_dates,
    )


def wb_streaming_supported(filename: str) -> bool:
    return Path(filename).suffix.lower() in {".xlsx", ".csv"}
