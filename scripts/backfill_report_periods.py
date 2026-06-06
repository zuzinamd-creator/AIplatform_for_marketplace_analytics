#!/usr/bin/env python3
"""Backfill sale-based report periods for all uploaded reports."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.tenant_context import set_bypass_rls_context
from app.domain.reports.period import attach_period_to_raw_data
from app.domain.reports.period_queries import fetch_sale_period_bounds_for_reports
from app.models.report import Report


def load_env() -> None:
    env = ROOT / ".env"
    if not env.is_file():
        return
    for line in env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


async def backfill_report_periods(
    db: AsyncSession,
    *,
    batch_size: int = 200,
    dry_run: bool = False,
) -> dict[str, int]:
    await set_bypass_rls_context(db, True)

    report_ids = list((await db.execute(select(Report.id).order_by(Report.created_at.asc()))).scalars().all())
    updated = 0
    cleared = 0
    unchanged = 0

    for offset in range(0, len(report_ids), batch_size):
        batch_ids = report_ids[offset : offset + batch_size]
        bounds = await fetch_sale_period_bounds_for_reports(db, batch_ids)
        reports = list(
            (await db.execute(select(Report).where(Report.id.in_(batch_ids)))).scalars().all()
        )
        for report in reports:
            period_start, period_end = bounds.get(report.id, (None, None))
            next_raw = attach_period_to_raw_data(
                report.raw_data,
                period_start=period_start,
                period_end=period_end,
            )
            current_raw = dict(report.raw_data or {})
            if current_raw.get("period_start") == next_raw.get("period_start") and current_raw.get(
                "period_end"
            ) == next_raw.get("period_end"):
                unchanged += 1
                continue
            if period_start is None and period_end is None:
                cleared += 1
            else:
                updated += 1
            if not dry_run:
                report.raw_data = next_raw
                db.add(report)

        if not dry_run:
            await db.commit()

    return {
        "reports_total": len(report_ids),
        "updated": updated,
        "cleared": cleared,
        "unchanged": unchanged,
        "dry_run": int(dry_run),
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env()
    database_url = os.environ.get("ALEMBIC_DATABASE_URL", os.environ.get("DATABASE_URL"))
    if not database_url:
        raise SystemExit("DATABASE_URL is not configured")

    engine = create_async_engine(database_url)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        stats = await backfill_report_periods(
            db,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )
    await engine.dispose()

    mode = "dry-run" if args.dry_run else "applied"
    print(
        f"[{mode}] reports_total={stats['reports_total']} "
        f"updated={stats['updated']} cleared={stats['cleared']} unchanged={stats['unchanged']}"
    )


if __name__ == "__main__":
    asyncio.run(main())
