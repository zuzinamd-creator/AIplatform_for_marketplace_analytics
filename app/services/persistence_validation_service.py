from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.environment import detect_environment
from app.core.security_context import TenantSession
from app.models.ai_execution import AIExecutionRun
from app.models.cost_history import CostHistory
from app.models.finance.ledger import FinancialLedgerEntry
from app.models.report import Report
from app.models.workflow import SellerWorkflowEvent


@dataclass(frozen=True)
class PersistenceStatus:
    environment_mode: str
    db_host: str
    db_name: str
    persistent_storage: bool
    total_reports: int
    total_cost_rows: int
    total_ledger_rows: int
    total_ai_runs: int
    total_workflows: int
    oldest_report: datetime | None
    newest_report: datetime | None


class PersistenceValidationService:
    def __init__(self, db: AsyncSession, *, user_id) -> None:
        self.db = db
        self.user_id = user_id

    async def status(self) -> PersistenceStatus:
        env = detect_environment()

        async with TenantSession.transaction(self.db, self.user_id):
            total_reports = int(
                (
                    await self.db.execute(
                        select(func.count()).select_from(Report)
                    )
                ).scalar_one()
            )
            total_cost_rows = int(
                (
                    await self.db.execute(
                        select(func.count()).select_from(CostHistory)
                    )
                ).scalar_one()
            )
            total_ledger_rows = int(
                (
                    await self.db.execute(
                        select(func.count()).select_from(FinancialLedgerEntry)
                    )
                ).scalar_one()
            )
            total_ai_runs = int(
                (
                    await self.db.execute(
                        select(func.count()).select_from(AIExecutionRun)
                    )
                ).scalar_one()
            )
            total_workflows = int(
                (
                    await self.db.execute(
                        select(func.count()).select_from(SellerWorkflowEvent)
                    )
                ).scalar_one()
            )
            oldest_report = (
                await self.db.execute(select(func.min(Report.created_at)))
            ).scalar_one_or_none()
            newest_report = (
                await self.db.execute(select(func.max(Report.created_at)))
            ).scalar_one_or_none()

        return PersistenceStatus(
            environment_mode=env.mode,
            db_host=env.db_host,
            db_name=env.db_name,
            persistent_storage=not env.is_ephemeral,
            total_reports=total_reports,
            total_cost_rows=total_cost_rows,
            total_ledger_rows=total_ledger_rows,
            total_ai_runs=total_ai_runs,
            total_workflows=total_workflows,
            oldest_report=oldest_report,
            newest_report=newest_report,
        )

