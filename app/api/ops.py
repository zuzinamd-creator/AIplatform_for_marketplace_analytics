"""Read-only operational visibility endpoints (tenant-scoped)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.ops import (
    DriftCheckOpsResponse,
    EtlAnomalyOpsResponse,
    PaginatedAnomaliesResponse,
    PaginatedDriftChecksResponse,
    PaginatedQueueResponse,
    PaginatedRebuildsResponse,
    QueueJobOpsResponse,
    RebuildRequirementOpsResponse,
    SemanticsStatusOpsResponse,
    SemanticsVersionOpsResponse,
)
from app.schemas.ops_enterprise import (
    AutonomyStatusResponse,
    OperationalForecastResponse,
    PaginatedRemediationHistoryResponse,
    RemediationHistoryItem,
    SchedulePolicyResponse,
    SimulationRequest,
    SimulationResponse,
)
from app.schemas.ops_runtime import RuntimeHealthResponse, RuntimeSummaryResponse
from app.services.ops_service import OpsService

router = APIRouter()


@router.get("/rebuilds", response_model=PaginatedRebuildsResponse)
async def list_rebuilds(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedRebuildsResponse:
    rows, total = await OpsService(db, current_user).list_rebuilds(
        skip=skip, limit=limit, status=status
    )
    return PaginatedRebuildsResponse(
        items=[RebuildRequirementOpsResponse.model_validate(r) for r in rows],
        page=OpsService.page_meta(total, skip, limit),
    )


@router.get("/anomalies", response_model=PaginatedAnomaliesResponse)
async def list_anomalies(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedAnomaliesResponse:
    rows, total = await OpsService(db, current_user).list_anomalies(skip=skip, limit=limit)
    return PaginatedAnomaliesResponse(
        items=[EtlAnomalyOpsResponse.model_validate(r) for r in rows],
        page=OpsService.page_meta(total, skip, limit),
    )


@router.get("/drift-checks", response_model=PaginatedDriftChecksResponse)
async def list_drift_checks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    consistent_only: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedDriftChecksResponse:
    rows, total = await OpsService(db, current_user).list_drift_checks(
        skip=skip, limit=limit, consistent_only=consistent_only
    )
    return PaginatedDriftChecksResponse(
        items=[DriftCheckOpsResponse.model_validate(r) for r in rows],
        page=OpsService.page_meta(total, skip, limit),
    )


@router.get("/queue", response_model=PaginatedQueueResponse)
async def list_queue(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedQueueResponse:
    rows, total, status_counts = await OpsService(db, current_user).list_queue_jobs(
        skip=skip, limit=limit
    )
    return PaginatedQueueResponse(
        items=[QueueJobOpsResponse.model_validate(r) for r in rows],
        page=OpsService.page_meta(total, skip, limit),
        status_counts=status_counts,
    )


@router.get("/dead-letters", response_model=PaginatedQueueResponse)
async def list_dead_letters(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedQueueResponse:
    rows, total = await OpsService(db, current_user).list_dead_letter_jobs(skip=skip, limit=limit)
    return PaginatedQueueResponse(
        items=[QueueJobOpsResponse.model_validate(r) for r in rows],
        page=OpsService.page_meta(total, skip, limit),
        status_counts={"dead_letter": total},
    )


@router.get("/runtime/health", response_model=RuntimeHealthResponse)
async def runtime_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RuntimeHealthResponse:
    return await OpsService(db, current_user).runtime_health()


@router.get("/runtime/summary", response_model=RuntimeSummaryResponse)
async def runtime_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RuntimeSummaryResponse:
    return await OpsService(db, current_user).runtime_summary()


@router.get("/runtime/autonomy/status", response_model=AutonomyStatusResponse)
async def autonomy_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AutonomyStatusResponse:
    return await OpsService(db, current_user).autonomy_status()


@router.get("/runtime/forecast", response_model=OperationalForecastResponse)
async def operational_forecast(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OperationalForecastResponse:
    return await OpsService(db, current_user).operational_forecast()


@router.post("/runtime/simulation", response_model=SimulationResponse)
async def run_operational_simulation(
    body: SimulationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SimulationResponse:
    return await OpsService(db, current_user).run_simulation(body.scenario)


@router.get("/runtime/schedules", response_model=SchedulePolicyResponse)
async def runtime_schedules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SchedulePolicyResponse:
    return await OpsService(db, current_user).schedule_policy()


@router.get("/runtime/remediation/history", response_model=PaginatedRemediationHistoryResponse)
async def remediation_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedRemediationHistoryResponse:
    rows, total = await OpsService(db, current_user).list_remediation_history(skip=skip, limit=limit)
    return PaginatedRemediationHistoryResponse(
        items=[RemediationHistoryItem.model_validate(r) for r in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/semantics-status", response_model=SemanticsStatusOpsResponse)
async def semantics_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SemanticsStatusOpsResponse:
    versions = await OpsService(db, current_user).semantics_status()
    return SemanticsStatusOpsResponse(
        versions=[SemanticsVersionOpsResponse.model_validate(v) for v in versions],
    )
