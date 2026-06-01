"""Synthetic multi-SKU inventory ledger datasets for scalability benchmarks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from app.core.security_context import TenantSession
from app.etl.db_batch import INSERT_BATCH_SIZE, iter_batches
from app.models.cost_history import CostHistory
from app.models.inventory import InventoryLedgerEntry
from app.models.inventory.enums import InventoryOperationType
from app.models.report import Marketplace, Report, ReportType
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

DEFAULT_SCALE_LEDGER_ROWS = 52_000
DEFAULT_SKU_COUNT = 200
DEFAULT_WAREHOUSE_COUNT = 5


@dataclass(frozen=True)
class ScaleDatasetSpec:
    ledger_rows: int
    sku_count: int
    warehouse_count: int
    days_span: int


@dataclass(frozen=True)
class ScaleTenantSeed:
    user_id: UUID
    report_id: UUID
    spec: ScaleDatasetSpec


def build_scale_spec(
    *,
    ledger_rows: int = DEFAULT_SCALE_LEDGER_ROWS,
    sku_count: int = DEFAULT_SKU_COUNT,
    warehouse_count: int = DEFAULT_WAREHOUSE_COUNT,
) -> ScaleDatasetSpec:
    if ledger_rows < 50_000:
        raise ValueError("scalability benchmark requires at least 50_000 ledger rows")
    keys = sku_count * warehouse_count
    if keys < 1:
        raise ValueError("sku_count * warehouse_count must be positive")
    rows_per_key = ledger_rows // keys
    if rows_per_key < 1:
        raise ValueError("ledger_rows too small for sku/warehouse cardinality")
    return ScaleDatasetSpec(
        ledger_rows=rows_per_key * keys,
        sku_count=sku_count,
        warehouse_count=warehouse_count,
        days_span=max(rows_per_key, 1),
    )


def _ledger_entries_for_spec(
    *,
    user_id: UUID,
    report_id: UUID,
    spec: ScaleDatasetSpec,
    base_date: date,
) -> list[InventoryLedgerEntry]:
    entries: list[InventoryLedgerEntry] = []
    keys = spec.sku_count * spec.warehouse_count
    cost = Decimal("10.00")
    sale = Decimal("25.00")
    base_created = datetime(2026, 1, 1, 12, 0, 0)

    for idx in range(spec.ledger_rows):
        key_index = idx % keys
        sku_index = key_index % spec.sku_count
        wh_index = key_index // spec.sku_count
        sku = f"SCALE-SKU-{sku_index:04d}"
        warehouse = f"SCALE-WH-{wh_index}"
        day_offset = idx // keys
        op_date = base_date + timedelta(days=day_offset % spec.days_span)
        inbound = idx % 4 == 0
        op_type = InventoryOperationType.INBOUND if inbound else InventoryOperationType.SALE
        qty = 8 if inbound else -1
        unit_cost = cost
        unit_sale = sale if not inbound else None
        total_cost = unit_cost * qty
        total_sale = (unit_sale or Decimal("0")) * qty

        entries.append(
            InventoryLedgerEntry(
                id=uuid4(),
                user_id=user_id,
                report_id=report_id,
                operation_date=op_date,
                sku=sku,
                nm_id=None,
                warehouse_name=warehouse,
                operation_type=op_type,
                quantity_delta=qty,
                cost_per_unit=unit_cost,
                sale_price_per_unit=unit_sale,
                total_cost_delta=total_cost,
                total_sale_delta=total_sale,
                source_row_id=f"scale-{idx:06d}",
                semantics_version="1.0",
                canonical_payload={"synthetic": True, "idx": idx},
                raw_payload={"synthetic": True},
                created_at=base_created + timedelta(microseconds=idx),
            )
        )
    return entries


async def seed_scale_tenant(
    session_factory: async_sessionmaker,
    spec: ScaleDatasetSpec,
    *,
    base_date: date = date(2026, 1, 1),
) -> ScaleTenantSeed:
    user_id = uuid4()
    report_id = uuid4()
    user = User(
        id=user_id,
        email=f"scale-{user_id}@example.com",
        hashed_password="scale-bench",
        is_active=True,
    )
    report = Report(
        id=report_id,
        user_id=user_id,
        marketplace=Marketplace.WILDBERRIES,
        report_type=ReportType.SALES,
        original_filename="scale_synthetic.csv",
        file_path="reports/scale_synthetic.csv",
        file_checksum=f"scale-{report_id}",
    )
    ledger_rows = _ledger_entries_for_spec(
        user_id=user_id,
        report_id=report_id,
        spec=spec,
        base_date=base_date,
    )

    async with session_factory() as session:
        async with session.begin():
            session.add(user)
            await session.flush()

    async with session_factory() as session:
        async with TenantSession.transaction(session, user_id):
            session.add(report)
            for sku_index in range(spec.sku_count):
                session.add(
                    CostHistory(
                        user_id=user_id,
                        internal_sku=f"SCALE-SKU-{sku_index:04d}",
                        cost=Decimal("10"),
                        product_cost=Decimal("10"),
                        packaging_cost=Decimal("0"),
                        inbound_logistics_cost=Decimal("0"),
                        additional_cost=Decimal("0"),
                        currency="RUB",
                        effective_from=base_date,
                    )
                )
            await session.flush()
            for batch in iter_batches(ledger_rows, batch_size=INSERT_BATCH_SIZE):
                session.add_all(batch)
            await session.flush()

    return ScaleTenantSeed(user_id=user_id, report_id=report_id, spec=spec)


async def stream_ledger_group_stats(
    session: AsyncSession,
    user_id: UUID,
) -> tuple[int, int, int]:
    """Return (ledger_rows, group_count, max_rows_per_group) from streaming replay."""
    from app.etl.wb.inventory_ledger_streaming import InventoryLedgerStreamingService

    stream = InventoryLedgerStreamingService(session, user_id).stream_grouped_by_key(
        rebuild_from=None,
        carry_forward_keys=set(),
    )
    ledger_rows = 0
    group_count = 0
    max_group = 0
    async for _key, rows in stream:
        group_count += 1
        size = len(rows)
        ledger_rows += size
        if size > max_group:
            max_group = size
    return ledger_rows, group_count, max_group
