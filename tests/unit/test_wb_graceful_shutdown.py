from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.security_context import TenantSession
from app.domain.reconciliation.calculator import ReconciliationCalculator
from app.etl.worker_shutdown import WorkerShutdownRequested
from app.etl.wb.persist import WbFinancialPersistService
from app.etl.wb.stream_process import WbStreamChunkIterator
from app.etl.wb.stream_types import WbProcessChunk
from app.parsers.wb.base import NormalizedWbRow
from app.parsers.wb.strategies.realization_v1 import RealizationV1Parser


def _minimal_row(index: int) -> NormalizedWbRow:
    return NormalizedWbRow(
        source_row_id=f"row-{index}",
        source_row_index=index,
        operation_date=None,
        sku="SKU1",
        nm_id=None,
        canonical={"sku": "SKU1", "operation_date": None},
        raw={"sku": "SKU1"},
    )


def test_stream_iterator_stops_before_next_chunk_when_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parser = RealizationV1Parser()
    stop = [False]

    def fake_iter(*_args, **_kwargs):
        yield parser, [_minimal_row(0)]
        yield parser, [_minimal_row(1)]

    monkeypatch.setattr(
        "app.etl.wb.stream_process.iter_wb_normalized_rows",
        fake_iter,
    )

    session = WbStreamChunkIterator(
        report_id=uuid4(),
        report_created_at=datetime.now(UTC),
        path=Path("/tmp/unused.xlsx"),
        filename="t.xlsx",
        shutdown_check=lambda: stop[0],
    )
    iterator = iter(session)
    next(iterator)
    stop[0] = True
    with pytest.raises(WorkerShutdownRequested) as exc_info:
        next(iterator)
    assert exc_info.value.chunks_completed == 1


@pytest.mark.asyncio
async def test_process_wb_streamed_commits_only_completed_chunks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.etl.wb import stream_pipeline

    parser = RealizationV1Parser()

    def fake_iter(*_args, **_kwargs):
        yield parser, [_minimal_row(0)]
        yield parser, [_minimal_row(1)]

    monkeypatch.setattr(
        "app.etl.wb.stream_process.iter_wb_normalized_rows",
        fake_iter,
    )

    persisted_rows: list[int] = []
    persist_count = [0]
    stop_after = {"n": 999}

    async def fake_persist_chunk(self, *, report, chunk, job_id=None) -> None:  # noqa: ARG001
        persisted_rows.append(len(chunk.normalized_rows))
        persist_count[0] += 1

    async def fake_load_costs(self, db, user_id) -> dict:  # noqa: ARG001
        return {}

    def shutdown_check() -> bool:
        return persist_count[0] >= stop_after["n"]

    async def fake_raw_row(self, **kwargs) -> None:  # noqa: ARG001
        return None

    monkeypatch.setattr(
        stream_pipeline.WbFinancialPersistService,
        "persist_phase1_chunk",
        fake_persist_chunk,
    )
    monkeypatch.setattr(
        stream_pipeline.WbFinancialPersistService,
        "load_cost_snapshots",
        fake_load_costs,
    )
    monkeypatch.setattr(
        stream_pipeline.WbFinancialPersistService,
        "persist_raw_report_row",
        fake_raw_row,
    )

    report = MagicMock()
    report.id = uuid4()
    report.created_at = datetime.now(UTC)
    report.file_checksum = "abc"
    report.file_path = "bucket/path"

    db = AsyncMock()
    path = tmp_path / "t.xlsx"
    path.write_bytes(b"x")

    async def run() -> None:
        await stream_pipeline.process_wb_streamed(
            db=db,
            user_id=uuid4(),
            report=report,
            path=path,
            filename="t.xlsx",
            shutdown_check=shutdown_check,
        )

    await run()
    assert persisted_rows == [1, 1]

    persisted_rows.clear()
    persist_count[0] = 0
    stop_after["n"] = 1
    with pytest.raises(WorkerShutdownRequested) as exc_info:
        await run()
    assert persisted_rows == [1]
    assert exc_info.value.chunks_completed == 1


@pytest.mark.asyncio
async def test_persist_phase1_chunk_rolls_back_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    tx_ended_with_error = False

    class BeginCtx:
        async def __aenter__(self) -> None:
            return None

        async def __aexit__(self, exc_type, exc, tb) -> bool:  # noqa: ARG002
            nonlocal tx_ended_with_error
            if exc_type is not None:
                tx_ended_with_error = True
            return False

    db = AsyncMock()
    db.begin = MagicMock(return_value=BeginCtx())

    @asynccontextmanager
    async def fake_transaction(session, user_id):  # noqa: ARG001
        async with session.begin():
            yield

    monkeypatch.setattr(TenantSession, "transaction", fake_transaction)

    service = WbFinancialPersistService(db, uuid4())
    report = MagicMock()
    report.id = uuid4()

    chunk = WbProcessChunk(
        parser_name="wb",
        parser_version="v1",
        normalized_rows=[_minimal_row(0)],
        ledger_entries=[],
        inventory_movements=[],
        reconciliation=ReconciliationCalculator.calculate([]),
    )

    async def failing_insert(**kwargs) -> None:  # noqa: ARG001
        raise RuntimeError("simulated db failure")

    monkeypatch.setattr(service, "_persist_phase1_chunk", failing_insert)

    with pytest.raises(RuntimeError, match="simulated"):
        await service.persist_phase1_chunk(report=report, chunk=chunk)

    assert tx_ended_with_error is True
