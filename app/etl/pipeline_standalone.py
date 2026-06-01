"""CLI entrypoint for manual ETL pipeline runs (operator/debug only)."""

from __future__ import annotations

import asyncio
import sys
from uuid import UUID

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security_context import SystemSession, TenantSession
from app.etl.pipeline import ETLPipeline
from app.etl.storage import read_report_file
from app.models.report import Report
from app.models.user import User
from app.services.report_service import ReportService


async def run_standalone(report_id: UUID) -> None:
    async with SessionLocal() as db:
        async with SystemSession.transaction(db):
            report = (
                await db.execute(select(Report).where(Report.id == report_id))
            ).scalar_one_or_none()
        if not report:
            raise SystemExit(f"Report {report_id} not found")
        if not report.file_path:
            raise SystemExit("Report has no file_path")

        user_id = report.user_id
        filename = report.original_filename
        file_path = report.file_path
        marketplace = report.marketplace
        report_type = report.report_type
        created_at = report.created_at

    content = read_report_file(file_path)
    etl_result = ETLPipeline.process_content(
        report_id=report_id,
        report_created_at=created_at,
        filename=filename,
        content=content,
        marketplace=marketplace,
        report_type=report_type,
    )

    async with SessionLocal() as db:
        async with TenantSession.transaction(db, user_id):
            report_row = (
                await db.execute(select(Report).where(Report.id == report_id))
            ).scalar_one_or_none()
            user_row = (
                await db.execute(select(User).where(User.id == user_id))
            ).scalar_one_or_none()
        if report_row is None or user_row is None:
            raise SystemExit("Report or user disappeared before persist")

        report_service = ReportService(db, user_row)
        pipeline = ETLPipeline(db, user_id)
        await pipeline.persist_result(report_row, etl_result, report_service)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m app.etl.pipeline_standalone <report_id>")
        raise SystemExit(1)
    try:
        report_id = UUID(sys.argv[1])
    except ValueError:
        raise SystemExit("Invalid UUID for report_id") from None
    print(f"[Pipeline] Standalone run for report {report_id}")
    asyncio.run(run_standalone(report_id))
    print(f"[Pipeline] Completed for report {report_id}")


if __name__ == "__main__":
    main()
