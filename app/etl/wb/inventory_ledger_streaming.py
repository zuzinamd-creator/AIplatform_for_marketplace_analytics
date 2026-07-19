"""Streaming inventory ledger replay (per SKU/warehouse group, deterministic order).

Phase 9.17-E — Safe Incremental Stream v1 (Variant B):
When ``rebuild_from`` and ``carry_forward_keys`` are set, SQL keeps:

* rows with ``operation_date >= rebuild_from`` (window), OR
* rows whose key is **not** in carry-forward (full history for hole keys)

This matches the previous Python post-filter contract without changing stock math.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date
from uuid import UUID

from sqlalchemy import String, column, exists, or_, select, values
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.inventory.ledger_row import InventoryLedgerRow
from app.models.inventory import InventoryLedgerEntry

LedgerKey = tuple[str | None, str | None, str | None]


def row_kept_by_variant_b(
    *,
    key: LedgerKey,
    operation_date: date,
    rebuild_from: date | None,
    carry_forward_keys: set[LedgerKey],
) -> bool:
    """Pure predicate mirroring Variant B SQL (for tests / equivalence)."""
    if rebuild_from is None or not carry_forward_keys:
        return True
    if operation_date >= rebuild_from:
        return True
    return key not in carry_forward_keys


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

        Variant B (9.17-E): when carry_forward_keys is non-empty and rebuild_from is set,
        pre-window rows for carry-forward keys are excluded in SQL (not after fetch).
        """
        carry_forward_keys = carry_forward_keys or set()
        stmt = select(InventoryLedgerEntry).where(InventoryLedgerEntry.user_id == self.user_id)

        if rebuild_from is not None and carry_forward_keys:
            carry_rows = [
                (
                    key[0] if key[0] is not None else None,
                    key[1] if key[1] is not None else None,
                    key[2] if key[2] is not None else None,
                )
                for key in carry_forward_keys
            ]
            carry_v = values(
                column("sku", String),
                column("nm_id", String),
                column("warehouse_name", String),
                name="carry_keys",
            ).data(carry_rows)
            carry_alias = carry_v.alias("carry_keys")
            in_carry = exists(
                select(1)
                .select_from(carry_alias)
                .where(
                    InventoryLedgerEntry.sku.is_not_distinct_from(carry_alias.c.sku),
                    InventoryLedgerEntry.nm_id.is_not_distinct_from(carry_alias.c.nm_id),
                    InventoryLedgerEntry.warehouse_name.is_not_distinct_from(
                        carry_alias.c.warehouse_name
                    ),
                )
            )
            stmt = stmt.where(
                or_(
                    InventoryLedgerEntry.operation_date >= rebuild_from,
                    ~in_carry,
                )
            )

        stmt = (
            stmt.order_by(
                InventoryLedgerEntry.sku.asc().nulls_first(),
                InventoryLedgerEntry.warehouse_name.asc().nulls_first(),
                InventoryLedgerEntry.operation_date,
                InventoryLedgerEntry.created_at,
                InventoryLedgerEntry.source_row_id,
            ).execution_options(stream_results=True)
        )

        current_key: LedgerKey | None = None
        current_rows: list[InventoryLedgerRow] = []

        stream = await self.db.stream(stmt)
        try:
            async for entry in stream.scalars():
                row = InventoryLedgerRow.from_entry(entry)
                key = (row.sku, row.nm_id, row.warehouse_name)
                if current_key is not None and key != current_key:
                    yield current_key, current_rows
                    current_rows = []
                current_key = key
                current_rows.append(row)
        finally:
            await stream.close()

        if current_key is not None and current_rows:
            yield current_key, current_rows
