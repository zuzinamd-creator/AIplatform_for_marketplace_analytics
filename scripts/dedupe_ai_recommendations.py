#!/usr/bin/env python3
"""Dismiss duplicate AI recommendations for a seller inbox."""

from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security_context import TenantSession
from app.models.ai_intelligence import AIRecommendation, SellerWorkflowState


async def dedupe(*, user_id: UUID, dry_run: bool = False) -> None:
    async with SessionLocal() as db:
        async with TenantSession.transaction(db, user_id):
            rows = (
                await db.scalars(
                    select(AIRecommendation)
                    .where(AIRecommendation.user_id == user_id)
                    .where(
                        AIRecommendation.seller_workflow_state.in_(
                            (SellerWorkflowState.ACTIVE.value, SellerWorkflowState.SAVED.value)
                        )
                    )
                    .order_by(AIRecommendation.created_at.desc())
                )
            ).all()

        seen_reports: set[str] = set()
        seen_workflows: set[str] = set()
        dismissed = 0
        kept = 0
        for row in rows:
            lineage = row.lineage or {}
            report_id = str(lineage.get("report_id") or "")
            workflow = row.workflow_type
            duplicate = False
            if report_id and report_id in seen_reports:
                duplicate = True
            elif not report_id and workflow in seen_workflows:
                duplicate = True

            if duplicate:
                print(f"  dismiss {row.id} workflow={workflow}")
                if not dry_run:
                    async with TenantSession.transaction(db, user_id):
                        r = await db.get(AIRecommendation, row.id)
                        if r is not None:
                            r.seller_workflow_state = SellerWorkflowState.DISMISSED.value
                dismissed += 1
            else:
                if report_id:
                    seen_reports.add(report_id)
                seen_workflows.add(workflow)
                kept += 1
                print(f"  keep {row.id} workflow={workflow}")

        print(f"done: dismissed={dismissed} kept={kept}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(dedupe(user_id=UUID(args.user_id), dry_run=args.dry_run))


if __name__ == "__main__":
    main()
