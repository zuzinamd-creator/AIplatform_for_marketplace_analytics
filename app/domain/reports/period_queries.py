"""DB queries for report sale-period bounds."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.reports.period import build_period_bounds_from_row_samples
from app.models.finance.normalized import NormalizedReportRow


async def fetch_sale_period_bounds_for_reports(
    db: AsyncSession,
    report_ids: list[UUID],
) -> dict[UUID, tuple[date | None, date | None]]:
    if not report_ids:
        return {}
    query = select(
        NormalizedReportRow.report_id,
        NormalizedReportRow.operation_date,
        NormalizedReportRow.canonical_payload,
    ).where(
        NormalizedReportRow.report_id.in_(report_ids),
        NormalizedReportRow.operation_date.is_not(None),
    )
    result = await db.execute(query)
    samples = (
        (
            report_id,
            operation_date,
            (canonical or {}).get("operation_type"),
        )
        for report_id, operation_date, canonical in result.all()
        if operation_date is not None
    )
    return build_period_bounds_from_row_samples(samples)
