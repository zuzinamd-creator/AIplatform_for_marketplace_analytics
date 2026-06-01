"""Streaming inventory ledger replay (per SKU/warehouse group, deterministic order)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.inventory.ledger_row import InventoryLedgerRow
from app.models.inventory import InventoryLedgerEntry

LedgerKey = tuple[str | None, str | None, str | None]


class InventoryLedgerStreamingService:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def stream_grouped_by_key(
        self,
        *,
        rebuild_from: date | None = None,
        carry_forward_keys: set[LedgerKey] | None = None,
    ) -> AsyncIterator[tuple[LedgerKey, list[InventoryLedgerRow]]]:
        """
        Stream tenant ledger ordered by sku, warehouse, date, created_at, source_row_id.

        When carry_forward_keys is set, rows before rebuild_from for those keys are skipped.
        """
        carry_forward_keys = carry_forward_keys or set()
        stmt = (
            select(InventoryLedgerEntry)
            .where(InventoryLedgerEntry.user_id == self.user_id)
            .order_by(
                InventoryLedgerEntry.sku.asc().nulls_first(),
                InventoryLedgerEntry.warehouse_name.asc().nulls_first(),
                InventoryLedgerEntry.operation_date,
                InventoryLedgerEntry.created_at,
                InventoryLedgerEntry.source_row_id,
            )
            .execution_options(stream_results=True)
        )

        current_key: LedgerKey | None = None
        current_rows: list[InventoryLedgerRow] = []

        stream = await self.db.stream(stmt)
        try:
            async for entry in stream.scalars():
                row = InventoryLedgerRow.from_entry(entry)
                key = (row.sku, row.nm_id, row.warehouse_name)
                if (
                    rebuild_from is not None
                    and key in carry_forward_keys
                    and row.operation_date < rebuild_from
                ):
                    continue
                if current_key is not None and key != current_key:
                    yield current_key, current_rows
                    current_rows = []
                current_key = key
                current_rows.append(row)
        finally:
            await stream.close()

        if current_key is not None and current_rows:
            yield current_key, current_rows
