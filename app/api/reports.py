from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.upload_stream import buffer_upload_with_checksum
from app.models.report import Marketplace, ReportType
from app.models.user import User
from app.schemas.report import ReportResponse, ReportUploadResponse
from app.schemas.report_mappers import report_to_response
from app.services.report_service import ReportService
from app.services.report_upload_service import persist_report_file, validate_report_file

router = APIRouter()


@router.post("/upload", response_model=ReportUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_report(
    marketplace: Marketplace = Form(...),
    report_type: ReportType = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportUploadResponse:
    filename = file.filename or "report.csv"
    spooled = await buffer_upload_with_checksum(file)

    try:
        validate_report_file(filename, spooled.read_all(), marketplace=marketplace)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    report_service = ReportService(db, current_user)
    existing = await report_service.find_by_checksum(spooled.checksum)
    if existing is not None:
        if existing.file_path is None:
            storage_path = persist_report_file(
                str(current_user.id),
                str(existing.id),
                filename,
                spooled.iter_chunks(),
            )
            job = await report_service.finalize_upload(
                existing,
                storage_path,
                file_size_bytes=spooled.size_bytes,
            )
            return ReportUploadResponse(
                report=report_to_response(existing, job),
                message="Report upload completed (resumed previous attempt)",
            )
        _, existing_job, _, _ = await report_service.get_report(existing.id)
        return ReportUploadResponse(
            report=report_to_response(existing, existing_job),
            message="Identical file already uploaded; returning existing report",
        )

    report = await report_service.create_report(
        marketplace=marketplace,
        report_type=report_type,
        original_filename=filename,
        file_path=None,
        file_checksum=spooled.checksum,
        raw_data=None,
        row_count=None,
    )

    storage_path = persist_report_file(
        str(current_user.id),
        str(report.id),
        filename,
        spooled.iter_chunks(),
    )

    job = await report_service.finalize_upload(
        report,
        storage_path,
        file_size_bytes=spooled.size_bytes,
    )

    ReportService(db, current_user).invalidate_list_cache()
    return ReportUploadResponse(
        report=report_to_response(report, job),
        message="Report uploaded, validated, and successfully queued for ETL processing",
    )


@router.get("", response_model=list[ReportResponse])
async def list_reports(
    skip: int = 0,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReportResponse]:
    return await ReportService(db, current_user).list_reports(skip=skip, limit=min(limit, 500))


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportResponse:
    report, job, ps, pe = await ReportService(db, current_user).get_report(report_id)
    return report_to_response(report, job, period_start=ps, period_end=pe)
