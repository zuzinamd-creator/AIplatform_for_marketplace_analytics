"""Row-count validation for streamed WB persist."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import FinancialLedgerEntry, NormalizedReportRow
from app.models.inventory import InventoryLedgerEntry


class WbRowCountMismatchError(ValueError):
    """Parsed or persisted row counts do not match report metadata."""


async def count_phase1_rows(db: AsyncSession, *, user_id: UUID, report_id: UUID) -> tuple[int, int, int]:
    norm = await db.scalar(
        select(func.count())
        .select_from(NormalizedReportRow)
        .where(
            NormalizedReportRow.user_id == user_id,
            NormalizedReportRow.report_id == report_id,
        )
    )
    ledger = await db.scalar(
        select(func.count())
        .select_from(FinancialLedgerEntry)
        .where(
            FinancialLedgerEntry.user_id == user_id,
            FinancialLedgerEntry.report_id == report_id,
        )
    )
    inventory = await db.scalar(
        select(func.count())
        .select_from(InventoryLedgerEntry)
        .where(
            InventoryLedgerEntry.user_id == user_id,
            InventoryLedgerEntry.report_id == report_id,
        )
    )
    return int(norm or 0), int(ledger or 0), int(inventory or 0)


def assert_row_count(
    *,
    label: str,
    actual: int,
    expected: int,
    report_id: UUID,
) -> None:
    if actual != expected:
        raise WbRowCountMismatchError(
            f"{label}: expected {expected} rows for report {report_id}, got {actual}"
        )
