#!/usr/bin/env python3
"""Rebuild ledger (from stored raw rows) and financial projections for all tenants."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.tenant_context import set_bypass_rls_context, set_current_user_context
from app.etl.wb.persist import WbFinancialPersistService
from app.models.finance.aggregates import DailyAggregate, SkuDailyMetric
from app.models.finance.ledger import FinancialLedgerEntry
from app.models.finance.normalized import NormalizedReportRow
from app.models.report import Report
from app.models.user import User


def load_env() -> None:
    env = ROOT / ".env"
    for line in env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


async def main() -> None:
    load_env()
    started = time.perf_counter()
    admin_url = os.environ.get("ALEMBIC_DATABASE_URL", os.environ["DATABASE_URL"])
    engine = create_async_engine(admin_url)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    total_reports = 0
    total_ledger = 0
    total_daily = 0
    total_sku = 0

    async with Session() as db:
        users = list((await db.execute(select(User.id, User.email))).all())
        report_count = (
            await db.execute(
                select(func.count(Report.id)).where(Report.row_count.is_not(None), Report.row_count > 0)
            )
        ).scalar_one()
        print(f"Tenants: {len(users)}, processed reports (row_count>0): {report_count}")

    for user_id, email in users:
        async with Session() as db:
            async with db.begin():
                await set_bypass_rls_context(db, True)
                await set_current_user_context(db, user_id)
                persist = WbFinancialPersistService(db, user_id)

                norm_count = (
                    await db.execute(
                        select(func.count(NormalizedReportRow.id)).where(
                            NormalizedReportRow.user_id == user_id
                        )
                    )
                ).scalar_one()
                if not norm_count:
                    print(f"{email}: skip (no normalized rows)")
                    continue

                dates = await persist.rebuild_ledger_from_normalized_rows()
                ledger_count = (
                    await db.execute(
                        select(func.count(FinancialLedgerEntry.id)).where(
                            FinancialLedgerEntry.user_id == user_id
                        )
                    )
                ).scalar_one()
                daily_count = (
                    await db.execute(
                        select(func.count(DailyAggregate.id)).where(DailyAggregate.user_id == user_id)
                    )
                ).scalar_one()
                sku_count = (
                    await db.execute(
                        select(func.count(SkuDailyMetric.id)).where(SkuDailyMetric.user_id == user_id)
                    )
                ).scalar_one()
                user_reports = (
                    await db.execute(
                        select(func.count(Report.id)).where(
                            Report.user_id == user_id,
                            Report.row_count.is_not(None),
                            Report.row_count > 0,
                        )
                    )
                ).scalar_one()

                total_reports += int(user_reports or 0)
                total_ledger += int(ledger_count or 0)
                total_daily += int(daily_count or 0)
                total_sku += int(sku_count or 0)
                print(
                    f"{email}: ledger={ledger_count} daily={daily_count} sku_metrics={sku_count} "
                    f"dates={len(dates)} reports={user_reports}"
                )

    elapsed = time.perf_counter() - started
    print(
        f"\nREBUILD COMPLETE in {elapsed:.1f}s | reports={total_reports} "
        f"ledger_entries={total_ledger} daily_aggregates={total_daily} sku_daily_metrics={total_sku}"
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
