"""Postgres advisory locks for per-tenant inventory snapshot rebuild serialization."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.inventory.errors import InventoryRebuildBusyError

# Dedicated namespace — do not reuse migration lock key.
INVENTORY_REBUILD_LOCK_NAMESPACE = 83472933


def inventory_rebuild_lock_keys(user_id: UUID) -> tuple[int, int]:
    """Map user_id to (namespace, key) pair for pg_try_advisory_xact_lock."""
    user_int = int(user_id.int % (2**31 - 1)) or 1
    return INVENTORY_REBUILD_LOCK_NAMESPACE, user_int


async def acquire_inventory_rebuild_lock(db: AsyncSession, user_id: UUID) -> None:
    """
    Non-blocking transaction-scoped exclusive lock for inventory snapshot rebuild.

    Raises InventoryRebuildBusyError immediately when another session holds the lock.
    """
    namespace, key = inventory_rebuild_lock_keys(user_id)
    result = await db.execute(
        text("SELECT pg_try_advisory_xact_lock(:namespace, :key)"),
        {"namespace": namespace, "key": key},
    )
    acquired = result.scalar_one()
    if not acquired:
        raise InventoryRebuildBusyError(user_id)
