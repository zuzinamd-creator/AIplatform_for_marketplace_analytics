"""
Stress / performance probe for WB processor + persist (RAM + wall time).

Self-contained module: delete this file to remove the test entirely.
Does not modify application code; calls WbFinancialProcessor.process() and
WbFinancialPersistService.persist() as-is.

Requires:
  RUN_INTEGRATION_TESTS=true
  RUN_STRESS_TESTS=true
  alembic upgrade head on TEST_DATABASE_URL
  tests/large_wb_report.xlsx

Run:
  pytest tests/integration/test_stress_processor.py -v -s
"""

from __future__ import annotations

import hashlib
import os
import time
import tracemalloc
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from app.core.security_context import TenantSession
from app.etl.wb.persist import WbFinancialPersistService
from app.etl.wb.processor import WbFinancialProcessor
from app.models.report import Marketplace, Report, ReportStatus, ReportType
from app.models.user import User
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

_STRESS_REPORT_PATH = Path(__file__).resolve().parent.parent / "large_wb_report.xlsx"


def _stress_enabled() -> bool:
    return os.getenv("RUN_STRESS_TESTS", "false").lower() == "true"


def _mb(num_bytes: int) -> float:
    return num_bytes / (1024 * 1024)


@dataclass(frozen=True)
class PhaseMetrics:
    name: str
    seconds: float
    peak_bytes: int

    @property
    def peak_mb(self) -> float:
        return _mb(self.peak_bytes)


@dataclass(frozen=True)
class StressMetrics:
    file_path: Path
    file_size_bytes: int
    row_count: int
    normalized_rows: int
    ledger_entries: int
    inventory_movements: int
    process: PhaseMetrics
    persist: PhaseMetrics | None
    persist_error: str | None = None

    @property
    def total_seconds(self) -> float:
        persist_seconds = self.persist.seconds if self.persist else 0.0
        return self.process.seconds + persist_seconds

    def format_report(self) -> str:
        lines = [
            "=== WB processor stress metrics ===",
            f"file: {self.file_path.name} ({_mb(self.file_size_bytes):.2f} MiB)",
            f"rows parsed: {self.row_count}",
            f"normalized_rows: {self.normalized_rows}",
            f"ledger_entries: {self.ledger_entries}",
            f"inventory_movements: {self.inventory_movements}",
            "",
            f"process(): {self.process.seconds:.3f}s, peak RAM {self.process.peak_mb:.2f} MiB",
        ]
        if self.persist is not None:
            lines.append(
                f"persist(): {self.persist.seconds:.3f}s, peak RAM {self.persist.peak_mb:.2f} MiB"
            )
        elif self.persist_error:
            lines.append(f"persist(): FAILED — {self.persist_error}")
        lines.append(f"total measured wall time: {self.total_seconds:.3f}s")
        return "\n".join(lines)


def _run_traced(callable_obj):
    """Run sync callable under tracemalloc; return (result, elapsed_s, peak_bytes)."""
    tracemalloc.start()
    started = time.perf_counter()
    try:
        result = callable_obj()
    finally:
        elapsed = time.perf_counter() - started
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return result, elapsed, peak


@pytest.fixture
def stress_report_path() -> Path:
    if not _stress_enabled():
        pytest.skip("Set RUN_STRESS_TESTS=true to run stress tests")
    if not _STRESS_REPORT_PATH.is_file():
        pytest.fail(f"Stress fixture missing: {_STRESS_REPORT_PATH}")
    return _STRESS_REPORT_PATH


@pytest.fixture
def stress_report_bytes(stress_report_path: Path) -> bytes:
    return stress_report_path.read_bytes()


@pytest.fixture
async def stress_tenant(
    db_session: AsyncSession,
) -> AsyncGenerator[tuple[User, list[UUID]], None]:
    """Creates an isolated user; deletes the user (and cascaded rows) after the test."""
    if not _stress_enabled():
        pytest.skip("Set RUN_STRESS_TESTS=true to run stress tests")

    user = User(
        id=uuid4(),
        email=f"stress-{uuid4()}@example.com",
        hashed_password="stress-test-hash",
        is_active=True,
    )
    report_ids: list[UUID] = []

    async with db_session.begin():
        db_session.add(user)
        await db_session.flush()

    try:
        yield user, report_ids
    finally:
        async with TenantSession.transaction(db_session, user.id):
            if report_ids:
                await db_session.execute(
                    delete(Report).where(Report.id.in_(report_ids))
                )
            await db_session.execute(delete(User).where(User.id == user.id))
            await db_session.flush()


@pytest.mark.integration
async def test_stress_wb_processor_ram_and_timing(
    db_session: AsyncSession,
    stress_report_path: Path,
    stress_report_bytes: bytes,
    stress_tenant: tuple[User, list],
) -> None:
    user, report_ids = stress_tenant
    content = stress_report_bytes
    created_at = datetime.now(UTC)
    report_id = uuid4()
    # Unique per run so a failed cleanup does not block the next stress run.
    file_checksum = hashlib.sha256(content + str(report_id).encode()).hexdigest()

    report = Report(
        id=report_id,
        user_id=user.id,
        marketplace=Marketplace.WILDBERRIES,
        report_type=ReportType.SALES,
        original_filename=stress_report_path.name,
        file_path=f"stress/{stress_report_path.name}",
        file_checksum=file_checksum,
        status=ReportStatus.PROCESSING,
    )
    report_ids.append(report.id)

    processed, process_seconds, process_peak = _run_traced(
        lambda: WbFinancialProcessor.process(
            report_id=report.id,
            report_created_at=created_at,
            filename=stress_report_path.name,
            content=content,
        )
    )
    assert processed.row_count > 0, "stress file produced no rows"

    persist_metrics: PhaseMetrics | None = None
    persist_error: str | None = None

    tracemalloc.start()
    persist_started = time.perf_counter()
    try:
        async with TenantSession.transaction(db_session, user.id):
            db_session.add(report)
            await db_session.flush()

            persist_service = WbFinancialPersistService(db_session, user.id)
            await persist_service.persist(
                report=report,
                file_checksum=file_checksum,
                storage_uri=report.file_path or "",
                result=processed,
            )
    except Exception as exc:
        persist_error = f"{type(exc).__name__}: {exc}"
    finally:
        persist_seconds = time.perf_counter() - persist_started
        _current, persist_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        if persist_error is None:
            persist_metrics = PhaseMetrics("persist", persist_seconds, persist_peak)

    metrics = StressMetrics(
        file_path=stress_report_path,
        file_size_bytes=len(content),
        row_count=processed.row_count,
        normalized_rows=len(processed.normalized_rows),
        ledger_entries=len(processed.ledger_entries),
        inventory_movements=len(processed.inventory_movements),
        process=PhaseMetrics("process", process_seconds, process_peak),
        persist=persist_metrics,
        persist_error=persist_error,
    )
    print(metrics.format_report())

    if persist_error is not None:
        pytest.fail(
            "persist() did not complete; process() metrics were printed above. "
            f"Cause: {persist_error}"
        )
