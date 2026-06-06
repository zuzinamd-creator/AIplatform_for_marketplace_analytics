"""DB queries for report sale-period bounds."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.reports.period import build_period_bounds_from_row_samples, is_wb_sale_payment_justification
from app.domain.reports.sale_date import extract_sale_date
from app.models.finance.normalized import NormalizedReportRow


async def fetch_sale_period_bounds_for_reports(
    db: AsyncSession,
    report_ids: list[UUID],
) -> dict[UUID, tuple[date | None, date | None]]:
    if not report_ids:
        return {}
    query = select(
        NormalizedReportRow.report_id,
        NormalizedReportRow.canonical_payload,
        NormalizedReportRow.raw_payload,
    ).where(NormalizedReportRow.report_id.in_(report_ids))
    result = await db.execute(query)
    samples: list[tuple[UUID, date, object]] = []
    for report_id, canonical, raw_payload in result.all():
        operation_label = (canonical or {}).get("operation_type")
        if not is_wb_sale_payment_justification(operation_label):
            continue
        sale_date = extract_sale_date(canonical=canonical, raw_payload=raw_payload)
        if sale_date is None:
            continue
        samples.append((report_id, sale_date, operation_label))
    return build_period_bounds_from_row_samples(samples)
