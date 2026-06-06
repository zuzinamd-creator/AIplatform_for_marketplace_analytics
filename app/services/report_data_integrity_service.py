"""Tenant-scoped integrity checks: reports ↔ etl_jobs ↔ storage paths ↔ costs."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security_context import TenantSession
from app.models.cost_history import CostHistory
from app.models.job import EtlJob
from app.models.report import Report


@dataclass(frozen=True)
class ReportDataIntegrityStatus:
    total_reports: int
    total_cost_rows: int
    reports_without_job: int
    reports_without_file_path: int
    orphan_etl_jobs: int
    sample_report_ids_without_job: list[UUID]

    @property
    def healthy(self) -> bool:
        return self.reports_without_job == 0 and self.orphan_etl_jobs == 0


class ReportDataIntegrityService:
    def __init__(self, db: AsyncSession, *, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def status(self) -> ReportDataIntegrityStatus:
        async with TenantSession.transaction(self.db, self.user_id):
            total_reports = int(
                (await self.db.execute(select(func.count()).select_from(Report))).scalar_one()
            )
            total_cost_rows = int(
                (await self.db.execute(select(func.count()).select_from(CostHistory))).scalar_one()
            )

            reports_without_job = int(
                (
                    await self.db.execute(
                        select(func.count())
                        .select_from(Report)
                        .where(
                            ~select(EtlJob.id)
                            .where(EtlJob.report_id == Report.id)
                            .correlate(Report)
                            .exists()
                        )
                    )
                ).scalar_one()
            )

            reports_without_file_path = int(
                (
                    await self.db.execute(
                        select(func.count())
                        .select_from(Report)
                        .where(Report.file_path.is_(None))
                    )
                ).scalar_one()
            )

            orphan_etl_jobs = int(
                (
                    await self.db.execute(
                        select(func.count())
                        .select_from(EtlJob)
                        .where(
                            ~select(Report.id)
                            .where(Report.id == EtlJob.report_id)
                            .correlate(EtlJob)
                            .exists()
                        )
                    )
                ).scalar_one()
            )

            sample_rows = (
                await self.db.execute(
                    select(Report.id)
                    .where(
                        ~select(EtlJob.id)
                        .where(EtlJob.report_id == Report.id)
                        .correlate(Report)
                        .exists()
                    )
                    .order_by(Report.created_at.desc())
                    .limit(5)
                )
            ).scalars().all()

        return ReportDataIntegrityStatus(
            total_reports=total_reports,
            total_cost_rows=total_cost_rows,
            reports_without_job=reports_without_job,
            reports_without_file_path=reports_without_file_path,
            orphan_etl_jobs=orphan_etl_jobs,
            sample_report_ids_without_job=list(sample_rows),
        )
