from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.persistence_validation_service import PersistenceValidationService
from app.services.report_data_integrity_service import ReportDataIntegrityService

router = APIRouter()


@router.get("/persistence-status")
async def persistence_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    status = await PersistenceValidationService(db, user_id=current_user.id).status()
    return {
        "environment": status.environment_mode,
        "db_host": status.db_host,
        "db_name": status.db_name,
        "persistent_storage": status.persistent_storage,
        "total_reports": status.total_reports,
        "total_cost_rows": status.total_cost_rows,
        "total_ledger_rows": status.total_ledger_rows,
        "total_ai_runs": status.total_ai_runs,
        "total_workflows": status.total_workflows,
        "oldest_report": status.oldest_report.isoformat() if status.oldest_report else None,
        "newest_report": status.newest_report.isoformat() if status.newest_report else None,
    }


@router.get("/data-integrity")
async def data_integrity(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    integrity = await ReportDataIntegrityService(db, user_id=current_user.id).status()
    return {
        "healthy": integrity.healthy,
        "total_reports": integrity.total_reports,
        "total_cost_rows": integrity.total_cost_rows,
        "reports_without_job": integrity.reports_without_job,
        "reports_without_file_path": integrity.reports_without_file_path,
        "orphan_etl_jobs": integrity.orphan_etl_jobs,
        "sample_report_ids_without_job": [
            str(rid) for rid in integrity.sample_report_ids_without_job
        ],
    }

