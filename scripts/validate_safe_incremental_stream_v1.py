#!/usr/bin/env python3
"""Fingerprint validation: full ledger rebuild vs Variant B filtered rebuild.

Exit 0 = IDENTICAL, exit 1 = DIFF.
Usage (ops): .venv/bin/python scripts/validate_safe_incremental_stream_v1.py
"""

from __future__ import annotations

import asyncio
import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal
from urllib.parse import unquote, urlparse
from uuid import UUID

import asyncpg

from app.core.config import settings
from app.domain.finance.types import SkuCostSnapshot
from app.domain.inventory.ledger_row import InventoryLedgerRow
from app.domain.inventory.pipeline import InventorySnapshotPipeline
from app.domain.inventory.snapshot_fingerprint import fingerprint_from_draft
from app.etl.wb.inventory_ledger_streaming import row_kept_by_variant_b
from app.models.inventory.enums import InventoryOperationType

# Pilot seller from 9.17-C evidence
DEFAULT_USER = UUID("caefecb3-5789-4878-a9d4-929be573fbcc")
REBUILD_FROM = date(2026, 7, 6)
REBUILD_TO = date(2026, 7, 12)


def _connect_args():
    raw = settings.async_database_url.replace("postgresql+asyncpg://", "postgresql://")
    p = urlparse(raw)
    return dict(
        host=p.hostname,
        port=p.port or 5432,
        user=unquote(p.username or ""),
        password=unquote(p.password or ""),
        database=p.path.lstrip("/"),
        ssl="require",
        statement_cache_size=0,
    )


async def main() -> int:
    user_id = DEFAULT_USER
    conn = await asyncpg.connect(**_connect_args())
    try:
        await conn.execute(f"SELECT set_config('app.current_user_id', '{user_id}', false)")
        await conn.execute("SELECT set_config('app.bypass_rls', 'true', false)")
        await conn.execute("SELECT set_config('app.queue_role', 'false', false)")

        # Carry-forward = latest actual_stock per key before rebuild_from (DISTINCT ON semantics)
        carry_rows = await conn.fetch(
            """
            SELECT DISTINCT ON (sku, nm_id, warehouse_name)
                   sku, nm_id, warehouse_name, actual_stock
            FROM warehouse_stock_snapshots
            WHERE user_id = $1::uuid AND snapshot_date < $2::date
            ORDER BY sku NULLS FIRST, nm_id NULLS FIRST, warehouse_name NULLS FIRST, snapshot_date DESC
            """,
            str(user_id),
            REBUILD_FROM,
        )
        carry: dict[tuple, int] = {
            (r["sku"], r["nm_id"], r["warehouse_name"]): int(r["actual_stock"]) for r in carry_rows
        }

        ledger = await conn.fetch(
            """
            SELECT operation_date, sku, nm_id, warehouse_name, operation_type,
                   quantity_delta, cost_per_unit, sale_price_per_unit,
                   semantics_version, source_row_id
            FROM inventory_ledger_entries
            WHERE user_id = $1::uuid
            ORDER BY sku NULLS FIRST, warehouse_name NULLS FIRST,
                     operation_date, created_at, source_row_id
            """,
            str(user_id),
        )
        costs_rows = await conn.fetch(
            """
            SELECT internal_sku, effective_from, product_cost, packaging_cost,
                   inbound_logistics_cost, additional_cost, currency
            FROM cost_history WHERE user_id = $1::uuid
            """,
            str(user_id),
        )
    finally:
        await conn.close()

    costs: dict[str, list[SkuCostSnapshot]] = defaultdict(list)
    for c in costs_rows:
        costs[c["internal_sku"]].append(
            SkuCostSnapshot(
                sku=c["internal_sku"],
                effective_from=c["effective_from"],
                product_cost=Decimal(str(c["product_cost"] or 0)),
                packaging_cost=Decimal(str(c["packaging_cost"] or 0)),
                inbound_logistics_cost=Decimal(str(c["inbound_logistics_cost"] or 0)),
                additional_cost=Decimal(str(c["additional_cost"] or 0)),
                currency=c["currency"] or "RUB",
            )
        )

    def to_row(r) -> InventoryLedgerRow:
        return InventoryLedgerRow(
            operation_date=r["operation_date"],
            sku=r["sku"],
            nm_id=r["nm_id"],
            warehouse_name=r["warehouse_name"],
            operation_type=InventoryOperationType(r["operation_type"]),
            quantity_delta=int(r["quantity_delta"]),
            cost_per_unit=Decimal(str(r["cost_per_unit"])) if r["cost_per_unit"] is not None else None,
            sale_price_per_unit=(
                Decimal(str(r["sale_price_per_unit"])) if r["sale_price_per_unit"] is not None else None
            ),
            semantics_version=r["semantics_version"] or "1.0",
            source_row_id=str(r["source_row_id"]),
        )

    all_rows = [to_row(r) for r in ledger]
    carry_keys = set(carry.keys())

    # OLD: full history per key, then domain window (initial_opening=None → walk history)
    by_key_full: dict[tuple, list[InventoryLedgerRow]] = defaultdict(list)
    for row in all_rows:
        by_key_full[(row.sku, row.nm_id, row.warehouse_name)].append(row)

    # NEW Variant B filter
    filtered = [
        row
        for row in all_rows
        if row_kept_by_variant_b(
            key=(row.sku, row.nm_id, row.warehouse_name),
            operation_date=row.operation_date,
            rebuild_from=REBUILD_FROM,
            carry_forward_keys=carry_keys,
        )
    ]
    by_key_new: dict[tuple, list[InventoryLedgerRow]] = defaultdict(list)
    for row in filtered:
        by_key_new[(row.sku, row.nm_id, row.warehouse_name)].append(row)

    old_fps: dict[tuple, str] = {}
    new_fps: dict[tuple, str] = {}
    old_stocks: dict[tuple, int] = {}
    new_stocks: dict[tuple, int] = {}

    keys = set(by_key_full) | set(by_key_new)
    for key in keys:
        full_movements = by_key_full.get(key, [])
        if not full_movements:
            continue
        old_snaps, _ = InventorySnapshotPipeline.rebuild(
            full_movements,
            costs_by_sku=dict(costs),
            rebuild_from=REBUILD_FROM,
            rebuild_to=REBUILD_TO,
            initial_opening=None,
        )
        new_movements = by_key_new.get(key, [])
        opening = carry.get(key)
        new_snaps, _ = InventorySnapshotPipeline.rebuild(
            new_movements,
            costs_by_sku=dict(costs),
            rebuild_from=REBUILD_FROM,
            rebuild_to=REBUILD_TO,
            initial_opening=opening,
        )
        for snap in old_snaps:
            k = (key, snap.snapshot_date)
            old_fps[k] = fingerprint_from_draft(snap)
            old_stocks[k] = snap.actual_stock
        for snap in new_snaps:
            k = (key, snap.snapshot_date)
            new_fps[k] = fingerprint_from_draft(snap)
            new_stocks[k] = snap.actual_stock

    only_old = set(old_fps) - set(new_fps)
    only_new = set(new_fps) - set(old_fps)
    mismatched = [
        k for k in set(old_fps) & set(new_fps) if old_fps[k] != new_fps[k] or old_stocks[k] != new_stocks[k]
    ]

    print(f"user={user_id}")
    print(f"window={REBUILD_FROM}..{REBUILD_TO}")
    print(f"ledger_rows={len(all_rows)} filtered_rows={len(filtered)} carry_keys={len(carry)}")
    print(f"old_snapshots={len(old_fps)} new_snapshots={len(new_fps)}")
    print(f"only_old={len(only_old)} only_new={len(only_new)} mismatched={len(mismatched)}")

    if only_old or only_new or mismatched:
        print("RESULT=DIFF")
        for k in list(mismatched)[:5]:
            print(f"  mismatch {k}: old={old_stocks.get(k)} new={new_stocks.get(k)}")
        for k in list(only_old)[:5]:
            print(f"  only_old {k}")
        for k in list(only_new)[:5]:
            print(f"  only_new {k}")
        return 1

    print("RESULT=IDENTICAL")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
