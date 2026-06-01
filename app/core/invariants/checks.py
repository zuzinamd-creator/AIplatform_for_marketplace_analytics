"""
Lightweight runtime invariant probes (log-only; never raise in production paths).

See docs/architecture/invariants.md for formal contracts.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.observability import get_logger
from app.domain.inventory.errors import UnsupportedSemanticsVersionError
from app.domain.inventory.snapshot_types import WarehouseStockSnapshotDraft
from app.domain.semantics.governance_policy import get_lifecycle_record
from app.models.inventory import WarehouseStockSnapshot
from app.models.inventory.staging import WarehouseStockSnapshotStaging

logger = get_logger("platform_invariants")

_NON_NEGATIVE_UNIT_FIELDS = (
    "inbound_units",
    "sold_units",
    "returned_units",
    "lost_units",
    "writeoff_units",
)


def log_invariant_violation(invariant_id: str, **details: object) -> None:
    """Structured warning; does not abort transactions or mutate ledger."""
    logger.warning(
        "platform_invariant_violation",
        extra={"invariant_id": invariant_id, **details},
    )


def check_snapshot_draft_batch(
    snapshots: Sequence[WarehouseStockSnapshotDraft],
    *,
    user_id: UUID | None = None,
    stage: str = "snapshot_draft",
) -> None:
    """In-memory checks before upsert/staging (O(n), no DB scan)."""
    if not snapshots:
        return

    seen: set[tuple[date, str | None, str | None]] = set()
    user_label = str(user_id) if user_id else None

    for snap in snapshots:
        key = (snap.snapshot_date, snap.sku, snap.warehouse_name)
        if key in seen:
            log_invariant_violation(
                "SNAP-UNIQUE-DAY-SKU-WH",
                user_id=user_label,
                stage=stage,
                snapshot_date=snap.snapshot_date.isoformat(),
                sku=snap.sku,
                warehouse_name=snap.warehouse_name,
            )
        seen.add(key)

        for field_name in _NON_NEGATIVE_UNIT_FIELDS:
            value = getattr(snap, field_name)
            if value < 0:
                log_invariant_violation(
                    "SNAP-NON-NEGATIVE-UNITS",
                    user_id=user_label,
                    stage=stage,
                    field=field_name,
                    value=value,
                    snapshot_date=snap.snapshot_date.isoformat(),
                    sku=snap.sku,
                )

        try:
            get_lifecycle_record(snap.semantics_version)
        except UnsupportedSemanticsVersionError:
            log_invariant_violation(
                "SEM-UNKNOWN-VERSION-DRAFT",
                user_id=user_label,
                stage=stage,
                semantics_version=snap.semantics_version,
                snapshot_date=snap.snapshot_date.isoformat(),
            )


async def check_promote_staging_row_match(
    db: AsyncSession,
    user_id: UUID,
    rebuild_run_id: UUID,
) -> None:
    """
    After promote_staging_to_live: live row count should match staging run size.

    Two indexed COUNT queries only; no full table scan beyond aggregates.
    """
    staging_count = (
        await db.execute(
            select(func.count())
            .select_from(WarehouseStockSnapshotStaging)
            .where(
                WarehouseStockSnapshotStaging.user_id == user_id,
                WarehouseStockSnapshotStaging.rebuild_run_id == rebuild_run_id,
            )
        )
    ).scalar_one()

    if staging_count == 0:
        return

    live_count = (
        await db.execute(
            select(func.count())
            .select_from(WarehouseStockSnapshot)
            .where(WarehouseStockSnapshot.user_id == user_id)
        )
    ).scalar_one()

    if live_count != staging_count:
        log_invariant_violation(
            "SNAP-PROMOTE-ROW-MISMATCH",
            user_id=str(user_id),
            rebuild_run_id=str(rebuild_run_id),
            staging_rows=int(staging_count),
            live_rows=int(live_count),
        )
