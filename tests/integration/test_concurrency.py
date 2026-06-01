"""
Concurrency / transaction-boundary checks for overlapping SKU imports.

Self-contained integration module (delete this file to remove the tests).
Calls production persist/rebuild paths only — no application code changes.

Requires:
  RUN_INTEGRATION_TESTS=true
  alembic upgrade head on TEST_DATABASE_URL

Run:
  pytest tests/integration/test_concurrency.py -v
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from app.core.inventory_rebuild_lock import acquire_inventory_rebuild_lock
from app.core.security_context import TenantSession
from app.domain.inventory.errors import InventoryRebuildBusyError
from app.etl.wb.inventory_snapshot_rebuild import InventorySnapshotRebuildService
from app.etl.wb.persist import WbFinancialPersistService
from app.etl.wb.processor import WbFinancialProcessor
from app.etl.wb.types import WbFinancialProcessResult
from app.models.cost_history import CostHistory
from app.models.finance import FinancialLedgerEntry, NormalizedReportRow
from app.models.inventory import InventoryLedgerEntry, WarehouseStockSnapshot
from app.models.report import Marketplace, Report, ReportStatus, ReportType
from app.models.user import User
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

SHARED_SKU = "SKU-CONC-1"
WAREHOUSE = "Коледино"

_REPORT_A_CSV = (
    "Дата продажи,Артикул поставщика,Тип операции,Кол-во,Цена розничная,"
    f"К перечислению,Склад,Комиссия\n"
    f"2026-01-10,{SHARED_SKU},Поступление,5,100,500,{WAREHOUSE},0\n"
).encode()

_REPORT_B_CSV = (
    "Дата продажи,Артикул поставщика,Тип операции,Кол-во,Цена розничная,"
    f"К перечислению,Склад,Комиссия\n"
    f"2026-01-11,{SHARED_SKU},Продажа,2,1000,800,{WAREHOUSE},-50\n"
).encode()


@dataclass(frozen=True)
class _PreparedReport:
    report: Report
    processed: WbFinancialProcessResult
    checksum: str


async def _cleanup_tenant(session_factory, user_id: UUID) -> None:
    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            await session.execute(delete(User).where(User.id == user_id))


async def _setup_tenant(session_factory) -> UUID:
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"concurrency-{user_id}@example.com",
        hashed_password="concurrency-test",
        is_active=True,
    )
    async with session_factory() as session:
        async with session.begin():
            session.add(user)
        async with TenantSession.transaction(session, user_id):
            session.add(
                CostHistory(
                    user_id=user_id,
                    internal_sku=SHARED_SKU,
                    cost=Decimal("10"),
                    product_cost=Decimal("10"),
                    packaging_cost=Decimal("0"),
                    inbound_logistics_cost=Decimal("0"),
                    additional_cost=Decimal("0"),
                    currency="RUB",
                    effective_from=date(2026, 1, 1),
                )
            )
            await session.flush()
    return user_id


def _prepare_report(
    user_id: UUID,
    *,
    filename: str,
    content: bytes,
    checksum_suffix: str,
) -> _PreparedReport:
    report_id = uuid4()
    checksum = f"conc-{checksum_suffix}-{report_id}"
    report = Report(
        id=report_id,
        user_id=user_id,
        marketplace=Marketplace.WILDBERRIES,
        report_type=ReportType.SALES,
        original_filename=filename,
        file_path=f"reports/{filename}",
        file_checksum=checksum,
        status=ReportStatus.PROCESSING,
    )
    processed = WbFinancialProcessor.process(
        report_id=report.id,
        report_created_at=datetime.now(UTC),
        filename=filename,
        content=content,
    )
    assert processed.row_count > 0
    return _PreparedReport(report=report, processed=processed, checksum=checksum)


async def _persist_prepared(
    session_factory,
    user_id: UUID,
    prepared: _PreparedReport,
    *,
    start_gate: asyncio.Event | None = None,
) -> None:
    if start_gate is not None:
        await start_gate.wait()
    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            session.add(prepared.report)
            await session.flush()
            service = WbFinancialPersistService(session, user_id)
            costs = await WbFinancialPersistService.load_cost_snapshots(session, user_id)
            enriched = WbFinancialProcessor.enrich_with_costs(prepared.processed, costs)
            await service.persist(
                report=prepared.report,
                file_checksum=prepared.checksum,
                storage_uri=prepared.report.file_path or "",
                result=enriched,
            )


async def _assert_tenant_data_consistent(
    session_factory,
    user_id: UUID,
    prepared_reports: list[_PreparedReport],
) -> None:
    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            snapshot_dupes = (
                await session.execute(
                    select(
                        WarehouseStockSnapshot.snapshot_date,
                        WarehouseStockSnapshot.sku,
                        WarehouseStockSnapshot.warehouse_name,
                        func.count(),
                    )
                    .where(WarehouseStockSnapshot.user_id == user_id)
                    .group_by(
                        WarehouseStockSnapshot.snapshot_date,
                        WarehouseStockSnapshot.sku,
                        WarehouseStockSnapshot.warehouse_name,
                    )
                    .having(func.count() > 1)
                )
            ).all()
            assert snapshot_dupes == [], f"duplicate snapshots: {snapshot_dupes}"

            for prepared in prepared_reports:
                report_id = prepared.report.id
                inv_count = (
                    await session.execute(
                        select(func.count())
                        .select_from(InventoryLedgerEntry)
                        .where(
                            InventoryLedgerEntry.user_id == user_id,
                            InventoryLedgerEntry.report_id == report_id,
                        )
                    )
                ).scalar_one()
                norm_count = (
                    await session.execute(
                        select(func.count())
                        .select_from(NormalizedReportRow)
                        .where(
                            NormalizedReportRow.user_id == user_id,
                            NormalizedReportRow.report_id == report_id,
                        )
                    )
                ).scalar_one()
                ledger_count = (
                    await session.execute(
                        select(func.count())
                        .select_from(FinancialLedgerEntry)
                        .where(
                            FinancialLedgerEntry.user_id == user_id,
                            FinancialLedgerEntry.report_id == report_id,
                        )
                    )
                ).scalar_one()

                expected_inv = len(prepared.processed.inventory_movements)
                expected_norm = len(prepared.processed.normalized_rows)
                assert inv_count == expected_inv, (
                    f"report {report_id}: inventory rows {inv_count} != {expected_inv}"
                )
                assert norm_count == expected_norm
                assert ledger_count <= len(prepared.processed.ledger_entries)

            day11 = (
                await session.execute(
                    select(WarehouseStockSnapshot).where(
                        WarehouseStockSnapshot.user_id == user_id,
                        WarehouseStockSnapshot.snapshot_date == date(2026, 1, 11),
                        WarehouseStockSnapshot.sku == SHARED_SKU,
                        WarehouseStockSnapshot.warehouse_name == WAREHOUSE,
                    )
                )
            ).scalar_one_or_none()
            if day11 is not None:
                assert day11.opening_stock == 5
                assert day11.expected_closing_stock == 3


@pytest.mark.integration
async def test_concurrent_persist_overlapping_skus_lock_and_consistency(db_engine) -> None:
    """
    Two reports for the same SKU persist in parallel.

    - No deadlocks (gather completes).
    - Rebuild advisory lock: one transaction wins, the other gets InventoryRebuildBusyError.
    - Retry of the loser succeeds; final DB state has no snapshot duplicates.
    """
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    user_id = await _setup_tenant(session_factory)

    try:
        report_a = _prepare_report(
            user_id,
            filename="conc_a.csv",
            content=_REPORT_A_CSV,
            checksum_suffix="a",
        )
        report_b = _prepare_report(
            user_id,
            filename="conc_b.csv",
            content=_REPORT_B_CSV,
            checksum_suffix="b",
        )

        start_gate = asyncio.Event()
        task_a = asyncio.create_task(
            _persist_prepared(session_factory, user_id, report_a, start_gate=start_gate)
        )
        task_b = asyncio.create_task(
            _persist_prepared(session_factory, user_id, report_b, start_gate=start_gate)
        )
        await asyncio.sleep(0)
        start_gate.set()
        results = await asyncio.wait_for(
            asyncio.gather(task_a, task_b, return_exceptions=True),
            timeout=120.0,
        )

        busy: list[_PreparedReport] = []
        succeeded: list[_PreparedReport] = []
        for prepared, outcome in zip((report_a, report_b), results, strict=True):
            if isinstance(outcome, InventoryRebuildBusyError):
                assert outcome.retryable is True
                busy.append(prepared)
            elif isinstance(outcome, Exception):
                raise outcome
            else:
                succeeded.append(prepared)

        assert len(succeeded) + len(busy) == 2
        if busy:
            assert len(succeeded) == 1, "when rebuild overlaps, one persist should win the lock"
            assert len(busy) == 1, "the other should fail fast with InventoryRebuildBusyError"
            for prepared in busy:
                await _persist_prepared(session_factory, user_id, prepared)

        await _assert_tenant_data_consistent(
            session_factory,
            user_id,
            [report_a, report_b],
        )
    finally:
        await _cleanup_tenant(session_factory, user_id)


@pytest.mark.integration
async def test_concurrent_snapshot_rebuild_only_one_runs(db_engine) -> None:
    """
    After both ledger layers are stored, parallel rebuild() calls contend on the same lock.
    """
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    user_id = await _setup_tenant(session_factory)

    try:
        report_a = _prepare_report(
            user_id,
            filename="rebuild_a.csv",
            content=_REPORT_A_CSV,
            checksum_suffix="ra",
        )
        report_b = _prepare_report(
            user_id,
            filename="rebuild_b.csv",
            content=_REPORT_B_CSV,
            checksum_suffix="rb",
        )

        for prepared in (report_a, report_b):
            await _persist_prepared(session_factory, user_id, prepared)

        rebuild_started = asyncio.Event()
        contender_done = asyncio.Event()

        async def holder_rebuild() -> None:
            async with session_factory() as session:
                async with TenantSession.transaction(session, user_id):
                    await acquire_inventory_rebuild_lock(session, user_id)
                    rebuild_started.set()
                    await asyncio.wait_for(contender_done.wait(), timeout=15.0)
                    service = InventorySnapshotRebuildService(session, user_id)
                    await service.rebuild(earliest_affected_date=date(2026, 1, 10))

        async def contender_rebuild() -> None:
            await rebuild_started.wait()
            try:
                async with session_factory() as session:
                    async with TenantSession.transaction(session, user_id):
                        service = InventorySnapshotRebuildService(session, user_id)
                        with pytest.raises(InventoryRebuildBusyError) as exc_info:
                            await service.rebuild(earliest_affected_date=date(2026, 1, 10))
                        assert exc_info.value.retryable is True
            finally:
                contender_done.set()

        await asyncio.wait_for(
            asyncio.gather(holder_rebuild(), contender_rebuild()),
            timeout=60.0,
        )

        await _assert_tenant_data_consistent(
            session_factory,
            user_id,
            [report_a, report_b],
        )
    finally:
        await _cleanup_tenant(session_factory, user_id)
