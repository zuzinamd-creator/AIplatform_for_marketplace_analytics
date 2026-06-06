#!/usr/bin/env python3
"""Backfill AI recommendations for processed finance reports (one run per report)."""

from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security_context import TenantSession
from app.dto.ai_analytics_dto import AIRunRequestDTO, AnalyticsWorkflow
from app.models.ai_insights import AIInsight
from app.models.ai_intelligence import AIRecommendation
from app.models.report import Report, ReportStatus, ReportType
from app.services.ai_service import AIService


async def _reports_pending_backfill(user_id: UUID) -> tuple[list[Report], int]:
    async with SessionLocal() as db:
        async with TenantSession.transaction(db, user_id):
            reports = (
                await db.scalars(
                    select(Report)
                    .where(
                        Report.user_id == user_id,
                        Report.report_type == ReportType.FINANCE,
                        Report.status == ReportStatus.PROCESSED,
                    )
                    .order_by(Report.created_at)
                )
            ).all()

            existing_report_ids = set(
                await db.scalars(
                    select(AIInsight.context_payload["report_id"].astext).where(  # type: ignore[index]
                        AIInsight.user_id == user_id,
                        AIInsight.id.in_(
                            select(AIRecommendation.insight_id).where(
                                AIRecommendation.user_id == user_id,
                                AIRecommendation.insight_id.isnot(None),
                            )
                        ),
                    )
                )
            )
            existing_report_ids.discard(None)

    pending = [r for r in reports if str(r.id) not in existing_report_ids]
    return pending, len(existing_report_ids)


async def backfill(*, user_id: UUID, dry_run: bool = False) -> None:
    pending, with_recs = await _reports_pending_backfill(user_id)
    print(f"user={user_id} with_recs={with_recs} pending={len(pending)}")

    for report in pending:
        print(f"  report {report.id}")
        if dry_run:
            continue
        request = AIRunRequestDTO(
            workflow=AnalyticsWorkflow.REVENUE_INSIGHT,
            prompt_id="analytics.summary.v1",
            semantics_version="1.0",
            report_id=report.id,
        )
        async with SessionLocal() as db:
            result = await AIService(db, user_id).run_intelligence(request)
        print(f"    -> recommendation_id={result.recommendation_id}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True, help="Seller UUID")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(backfill(user_id=UUID(args.user_id), dry_run=args.dry_run))


if __name__ == "__main__":
    main()
