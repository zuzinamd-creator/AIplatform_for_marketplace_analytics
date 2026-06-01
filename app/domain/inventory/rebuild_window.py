from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RebuildWindow:
    """Inclusive snapshot rebuild date range."""

    rebuild_from: date
    rebuild_to: date


def compute_rebuild_window(
    *,
    earliest_affected_date: date,
    latest_snapshot_date: date | None,
    latest_ledger_date: date | None,
) -> RebuildWindow:
    """
    Determine inclusive snapshot rebuild window.

    A balance change on date T invalidates every snapshot on T and all later dates.
    The window therefore extends to the latest existing snapshot horizon, not only
    the current report's ledger dates.

    rebuild_from = earliest_affected_date
    rebuild_to = max(latest_existing_snapshot_date, latest_ledger_date)
    """
    rebuild_from = earliest_affected_date

    horizon_end = earliest_affected_date
    if latest_snapshot_date is not None and latest_snapshot_date > horizon_end:
        horizon_end = latest_snapshot_date
    if latest_ledger_date is not None and latest_ledger_date > horizon_end:
        horizon_end = latest_ledger_date

    rebuild_to = horizon_end

    if rebuild_from > rebuild_to:
        raise ValueError(
            f"Invalid rebuild window: rebuild_from {rebuild_from} > rebuild_to {rebuild_to}"
        )

    return RebuildWindow(rebuild_from=rebuild_from, rebuild_to=rebuild_to)
