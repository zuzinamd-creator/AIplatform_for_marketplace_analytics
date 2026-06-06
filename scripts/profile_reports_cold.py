#!/usr/bin/env python3
"""Break down cold GET /reports latency: network, RLS, SQL, serialization."""

from __future__ import annotations

import asyncio
import os
import statistics
import time
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select, text

from app.core.database import SessionLocal
from app.core.tenant_context import set_current_user_context, set_queue_role_context
from app.models.finance.ledger import FinancialLedgerEntry
from app.models.job import EtlJob
from app.models.report import Report
from app.models.user import User
from app.services.report_service import ReportService, _reports_list_cache


def _load_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)


async def _timed(label: str, coro) -> object:
    start = time.perf_counter()
    result = await coro
    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"{label:42s} {elapsed_ms:8.1f} ms")
    return result


async def main() -> None:
    _load_env()
    default_test_id = os.environ.get("MVP_TEST_USER_ID", "c4fcd1f7-b315-4ade-bfa1-e804d69ab680")
    user_id = UUID(os.environ.get("PROFILE_USER_ID", default_test_id))

    _reports_list_cache._entries.clear()

    async with SessionLocal() as db:
        user = await db.get(User, user_id)
        if user is None:
            raise SystemExit(f"User not found: {user_id}")

    async with SessionLocal() as db:
        async with db.begin():
            await set_queue_role_context(db, False)
            await set_current_user_context(db, user_id)
            report_count = (await db.execute(select(func.count()).select_from(Report))).scalar_one()
            job_count = (
                await db.execute(select(func.count()).select_from(EtlJob).where(EtlJob.report_id.isnot(None)))
            ).scalar_one()
            ledger_count = (await db.execute(select(func.count()).select_from(FinancialLedgerEntry))).scalar_one()
        print(f"tenant={user.email} reports={report_count} jobs={job_count} ledger_rows={ledger_count}")
        print()

    async with SessionLocal() as db:
        await _timed("network: SELECT 1", db.execute(text("SELECT 1")))

    async with SessionLocal() as db:
        async def rls_ping() -> None:
            async with db.begin():
                await set_queue_role_context(db, False)
                await set_current_user_context(db, user_id)
                await db.execute(text("SELECT 1"))

        await _timed("RLS txn + set_config + SELECT 1", rls_ping())

    async with SessionLocal() as db:
        svc = ReportService(db, user)
        query = (
            select(Report)
            .where(Report.user_id == user_id)
            .order_by(Report.created_at.desc())
            .limit(50)
        )

        async def fetch_reports() -> list[Report]:
            async with svc._rls_transaction():
                return list((await svc.db.execute(query)).scalars().all())

        reports = await _timed("SQL: reports list (in RLS txn)", fetch_reports())
        report_ids = [r.id for r in reports]

        async def fetch_jobs() -> dict:
            async with svc._rls_transaction():
                return await svc._latest_jobs_for_reports(report_ids)

        await _timed("SQL: latest etl_jobs per report", fetch_jobs())

        async def fetch_bounds() -> dict:
            async with svc._rls_transaction():
                return await svc._period_bounds_for_report_ids(report_ids)

        await _timed("SQL: ledger period bounds GROUP BY", fetch_bounds())

    cold_samples: list[float] = []
    for _ in range(3):
        _reports_list_cache._entries.clear()
        async with SessionLocal() as db:
            svc = ReportService(db, user)
            start = time.perf_counter()
            rows = await svc.list_reports(skip=0, limit=50)
            cold_samples.append((time.perf_counter() - start) * 1000)

            start = time.perf_counter()
            payload = [row.model_dump() for row in rows]
            ser_ms = (time.perf_counter() - start) * 1000
        print(f"{'service.list_reports (cold)':42s} {cold_samples[-1]:8.1f} ms")
        print(f"{'serialization model_dump x'+str(len(payload)):42s} {ser_ms:8.1f} ms")

    print()
    print(f"cold median: {statistics.median(cold_samples):.0f} ms  samples={cold_samples}")


if __name__ == "__main__":
    asyncio.run(main())
