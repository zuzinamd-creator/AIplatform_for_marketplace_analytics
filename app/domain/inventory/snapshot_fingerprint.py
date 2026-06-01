"""Deterministic fingerprints for snapshot drift detection (no timestamps)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.domain.inventory.ledger_row import InventoryLedgerRow
from app.domain.inventory.snapshot_types import WarehouseStockSnapshotDraft
from app.models.inventory.snapshot import WarehouseStockSnapshot
from app.parsers.wb.semantics_registry import collect_semantics_versions


def resolve_semantics_version(rows: list[InventoryLedgerRow]) -> str:
    versions = collect_semantics_versions(rows)
    if not versions:
        return "1.0"
    return max(versions)


def snapshot_state_fingerprint(
    *,
    opening_stock: int,
    inbound_units: int,
    sold_units: int,
    returned_units: int,
    lost_units: int,
    writeoff_units: int,
    actual_stock: int,
    discrepancy_units: int,
    semantics_version: str,
) -> str:
    payload: dict[str, Any] = {
        "opening_stock": opening_stock,
        "inbound_units": inbound_units,
        "sold_units": sold_units,
        "returned_units": returned_units,
        "lost_units": lost_units,
        "writeoff_units": writeoff_units,
        "actual_stock": actual_stock,
        "discrepancy_units": discrepancy_units,
        "semantics_version": semantics_version,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def fingerprint_from_draft(snap: WarehouseStockSnapshotDraft) -> str:
    return snapshot_state_fingerprint(
        opening_stock=snap.opening_stock,
        inbound_units=snap.inbound_units,
        sold_units=snap.sold_units,
        returned_units=snap.returned_units,
        lost_units=snap.lost_units,
        writeoff_units=snap.writeoff_units,
        actual_stock=snap.actual_stock,
        discrepancy_units=snap.discrepancy_units,
        semantics_version=snap.semantics_version,
    )


def fingerprint_from_model(snap: WarehouseStockSnapshot) -> str:
    return snapshot_state_fingerprint(
        opening_stock=snap.opening_stock,
        inbound_units=snap.inbound_units,
        sold_units=snap.sold_units,
        returned_units=snap.returned_units,
        lost_units=snap.lost_units,
        writeoff_units=snap.writeoff_units,
        actual_stock=snap.actual_stock,
        discrepancy_units=snap.discrepancy_units,
        semantics_version=snap.semantics_version,
    )


def ledger_day_fingerprint(rows: list[InventoryLedgerRow]) -> str:
    """Hash of ordered ledger movements for one snapshot day (deterministic replay)."""
    ordered = sorted(
        rows,
        key=lambda row: (
            row.operation_date,
            row.source_row_id,
            row.operation_type.value,
            row.quantity_delta,
            row.semantics_version,
        ),
    )
    parts: list[dict[str, Any]] = []
    for row in ordered:
        parts.append(
            {
                "source_row_id": row.source_row_id,
                "operation_type": row.operation_type.value,
                "quantity_delta": row.quantity_delta,
                "semantics_version": row.semantics_version,
            }
        )
    canonical = json.dumps(parts, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
