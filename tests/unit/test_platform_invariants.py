"""Runtime invariant probes are log-only and must not raise."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.invariants.checks import check_snapshot_draft_batch
from app.domain.inventory.snapshot_types import WarehouseStockSnapshotDraft


def _draft(**kwargs: object) -> WarehouseStockSnapshotDraft:
    defaults = {
        "snapshot_date": date(2026, 1, 10),
        "sku": "SKU-A",
        "nm_id": None,
        "warehouse_name": "WH-1",
        "opening_stock": 0,
        "inbound_units": 1,
        "sold_units": 0,
        "returned_units": 0,
        "lost_units": 0,
        "writeoff_units": 0,
        "expected_closing_stock": 1,
        "actual_stock": 1,
        "discrepancy_units": 0,
        "discrepancy_cost": Decimal("0"),
        "discrepancy_sale_value": Decimal("0"),
        "semantics_version": "1.0",
    }
    defaults.update(kwargs)
    return WarehouseStockSnapshotDraft(**defaults)  # type: ignore[arg-type]


def test_check_snapshot_draft_batch_does_not_raise_on_duplicates() -> None:
    dup = _draft()
    with patch("app.core.invariants.checks.logger") as log:
        check_snapshot_draft_batch([dup, dup])
        assert log.warning.called


def test_check_snapshot_draft_batch_does_not_raise_on_negative_units() -> None:
    bad = _draft(sold_units=-1)
    with patch("app.core.invariants.checks.logger") as log:
        check_snapshot_draft_batch([bad])
        assert log.warning.called
        assert any(
            call.kwargs.get("extra", {}).get("invariant_id") == "SNAP-NON-NEGATIVE-UNITS"
            for call in log.warning.call_args_list
        )


def test_check_snapshot_draft_batch_unknown_semantics_logs_only() -> None:
    bad = _draft(semantics_version="99.9")
    with patch("app.core.invariants.checks.logger") as log:
        check_snapshot_draft_batch([bad])
        assert log.warning.called


@pytest.mark.asyncio
async def test_check_promote_staging_row_match_logs_mismatch() -> None:
    from uuid import uuid4

    from app.core.invariants.checks import check_promote_staging_row_match

    user_id = uuid4()
    run_id = uuid4()
    db = MagicMock()
    staging_result = MagicMock()
    staging_result.scalar_one.return_value = 10
    live_result = MagicMock()
    live_result.scalar_one.return_value = 7
    db.execute = AsyncMock(side_effect=[staging_result, live_result])

    with patch("app.core.invariants.checks.logger") as log:
        await check_promote_staging_row_match(db, user_id, run_id)
        assert log.warning.called
