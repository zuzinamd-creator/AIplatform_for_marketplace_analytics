"""
Phase-3 aggregate rebuild under row-lock contention (two workers).

Requires RUN_INTEGRATION_TESTS=true and TEST_DATABASE_URL with Alembic schema.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from app.core.queue.etl_retry_policy import EtlRetryableError, RetryReason
from app.core.queue.postgres_backend import PostgresQueueBackend
from app.core.security_context import TenantSession
from app.domain.reconciliation.calculator import ReconciliationCalculator
from app.models.finance.enums import LedgerOperationType
from app.etl.pg_timeouts import set_local_lock_timeout
from app.etl.wb.persist import WbFinancialPersistService
from app.etl.wb.types import WbFinancialProcessResult
from app.models.cost_history import CostHistory
from app.models.finance import DailyAggregate, FinancialLedgerEntry, SkuDailyMetric
from app.models.job import EtlJob, JobStatus
from app.models.report import Marketplace, Report, ReportStatus, ReportType
from app.models.user import User
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.integration

METRIC_DATE = date(2026, 2, 10)
SKU_A = "SKU-LOCK-A"
SKU_B = "SKU-LOCK-B"


async def _seed_tenant(session_factory, user_id) -> None:
    user = User(
        id=user_id,
        email=f"phase3-lock-{user_id}@example.com",
        hashed_password="test",
        is_active=True,
    )
    async with session_factory() as session:
        async with session.begin():
            session.add(user)
        async with TenantSession.transaction(session, user_id):
            session.add(
                CostHistory(
                    user_id=user_id,
                    internal_sku=SKU_A,
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


def _streamed_result(report_id, user_id) -> WbFinancialProcessResult:
    return WbFinancialProcessResult(
        report_id=report_id,
        parser_name="wb",
        parser_version="v1",
        raw_snapshot={"columns": [], "row_count": 2, "sample_rows": []},
        normalized_rows=[],
        ledger_entries=[],
        inventory_movements=[],
        reconciliation=ReconciliationCalculator.calculate([]),
        daily_aggregates=[],
        sku_daily_metrics=[],
        analytics_payload={},  # type: ignore[arg-type]
        default_date=METRIC_DATE,
        row_count=2,
        streamed=True,
        earliest_movement_date=METRIC_DATE,
    )


async def _seed_ledger(session_factory, user_id, report_id) -> None:
    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            rows = [
                FinancialLedgerEntry(
                    user_id=user_id,
                    report_id=report_id,
                    operation_date=METRIC_DATE,
                    sku=SKU_A,
                    nm_id=None,
                    operation_type=LedgerOperationType.SALE,
                    amount=Decimal("100"),
                    currency="RUB",
                    source_row_id="row-1",
                    entry_metadata={},
                ),
                FinancialLedgerEntry(
                    user_id=user_id,
                    report_id=report_id,
                    operation_date=METRIC_DATE,
                    sku=SKU_B,
                    nm_id=None,
                    operation_type=LedgerOperationType.SALE,
                    amount=Decimal("200"),
                    currency="RUB",
                    source_row_id="row-2",
                    entry_metadata={},
                ),
            ]
            session.add_all(rows)
            await session.flush()


@pytest.mark.asyncio
async def test_phase3_lock_timeout_then_retry_produces_consistent_aggregates(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    user_id = uuid4()
    report_id = uuid4()
    await _seed_tenant(session_factory, user_id)
    await _seed_ledger(session_factory, user_id, report_id)

    report = Report(
        id=report_id,
        user_id=user_id,
        marketplace=Marketplace.WILDBERRIES,
        report_type=ReportType.SALES,
        original_filename="lock.xlsx",
        file_path="reports/lock.xlsx",
        file_checksum="checksum-lock-test",
        status=ReportStatus.PROCESSING,
    )
    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            session.add(report)
            await session.flush()

    result = _streamed_result(report_id, user_id)
    lock_ready = asyncio.Event()
    release_lock = asyncio.Event()

    async def worker_holding_row_lock() -> None:
        async with session_factory() as session:
            async with TenantSession.transaction(session, user_id):
                await session.execute(
                    insert(DailyAggregate)
                    .values(
                        user_id=user_id,
                        aggregate_date=METRIC_DATE,
                        marketplace=Marketplace.WILDBERRIES,
                        revenue=Decimal("0"),
                        net_profit=Decimal("0"),
                        margin=None,
                        roi=None,
                        return_rate=None,
                        buyout_rate=None,
                        average_check=None,
                        units_sold=0,
                    )
                    .on_conflict_do_nothing(constraint="uq_daily_aggregate_day_marketplace")
                )
                await session.flush()
                await session.execute(
                    select(DailyAggregate)
                    .where(
                        DailyAggregate.user_id == user_id,
                        DailyAggregate.aggregate_date == METRIC_DATE,
                    )
                    .with_for_update()
                )
                lock_ready.set()
                await asyncio.wait_for(release_lock.wait(), timeout=10.0)

    async def worker_rebuild_with_short_lock_timeout() -> None:
        await lock_ready.wait()
        async with session_factory() as session:
            async with TenantSession.transaction(session, user_id):
                await set_local_lock_timeout(session, timeout_ms=200)
                service = WbFinancialPersistService(session, user_id)
                with pytest.raises(EtlRetryableError) as exc_info:
                    await service._rebuild_aggregates(result=result, report_id=report_id)
                assert exc_info.value.retry_reason == RetryReason.LOCK_TIMEOUT

    holder = asyncio.create_task(worker_holding_row_lock())
    try:
        await asyncio.wait_for(worker_rebuild_with_short_lock_timeout(), timeout=15.0)
    finally:
        release_lock.set()
        await holder

    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            service = WbFinancialPersistService(session, user_id)
            await service._rebuild_aggregates(result=result, report_id=report_id)
            await session.flush()

    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            skus = (
                await session.execute(
                    select(SkuDailyMetric.sku, SkuDailyMetric.revenue).where(
                        SkuDailyMetric.user_id == user_id,
                        SkuDailyMetric.metric_date == METRIC_DATE,
                    )
                )
            ).all()
            by_sku = {sku: revenue for sku, revenue in skus}
            assert by_sku.get(SKU_A) == Decimal("100")
            assert by_sku.get(SKU_B) == Decimal("200")
            daily = (
                await session.execute(
                    select(DailyAggregate.revenue).where(
                        DailyAggregate.user_id == user_id,
                        DailyAggregate.aggregate_date == METRIC_DATE,
                    )
                )
            ).scalar_one()
            assert daily == Decimal("300")


@pytest.mark.asyncio
async def test_queue_backoff_blocks_immediate_reclaim(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    user_id = uuid4()
    report_id = uuid4()
    job_id = uuid4()
    now = datetime.now(UTC)

    async with session_factory() as session:
        async with session.begin():
            session.add(
                User(
                    id=user_id,
                    email=f"queue-backoff-{user_id}@example.com",
                    hashed_password="x",
                    is_active=True,
                )
            )
        async with TenantSession.transaction(session, user_id):
            session.add(
                EtlJob(
                    id=job_id,
                    user_id=user_id,
                    report_id=report_id,
                    job_type="etl_process_report",
                    status=JobStatus.PROCESSING,
                    attempt_count=1,
                    max_attempts=3,
                    idempotency_key=f"backoff-{job_id}",
                    file_path="local/t.xlsx",
                    marketplace=Marketplace.WILDBERRIES.value,
                    report_type=ReportType.SALES.value,
                    original_filename="t.xlsx",
                    report_created_at=now,
                    claimed_at=now,
                    processing_started_at=now,
                )
            )
            await session.flush()

        backend = PostgresQueueBackend(session)
        await backend.fail(
            str(job_id),
            error_message="lock timeout during phase 3",
            attempt_count=1,
            max_attempts=3,
            retry_reason=RetryReason.LOCK_TIMEOUT,
        )
        await session.commit()

    async with session_factory() as session:
        claimed = await PostgresQueueBackend(session).claim()
        assert claimed is None

        row = (
            await session.execute(select(EtlJob).where(EtlJob.id == job_id))
        ).scalar_one()
        assert row.status == JobStatus.PENDING
        assert row.processing_started_at is not None
        assert row.processing_started_at > datetime.now(UTC)
