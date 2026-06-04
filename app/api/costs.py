from datetime import date
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.template_paths import (
    COST_IMPORT_TEMPLATE_FILENAME,
    cost_import_template_path,
    cost_import_template_resolution,
)
from app.models.user import User
from app.schemas.cost import CostCreateRequest, CostResponse, CostUpdateRequest
from app.schemas.cost_import import CostImportPreviewResponse, CostImportResultResponse
from app.services.cost_service import CostService

router = APIRouter()


@router.post("", response_model=CostResponse, status_code=201)
async def create_cost(
    payload: CostCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CostResponse:
    row = await CostService(db, current_user).create_cost(
        internal_sku=payload.internal_sku,
        effective_from=payload.effective_from,
        product_cost=payload.product_cost,
        packaging_cost=payload.packaging_cost,
        inbound_logistics_cost=payload.inbound_logistics_cost,
        additional_cost=payload.additional_cost,
        currency=payload.currency,
        comment=payload.comment,
    )
    return CostResponse.model_validate(row)


@router.get("", response_model=list[CostResponse])
async def list_costs(
    sku: str | None = None,
    as_of: date | None = None,
    effective_from: date | None = None,
    effective_to: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CostResponse]:
    rows = await CostService(db, current_user).list_costs(
        sku=sku,
        as_of=as_of,
        effective_from=effective_from,
        effective_to=effective_to,
    )
    return [CostResponse.model_validate(row) for row in rows]


@router.patch("/{cost_id}", response_model=CostResponse)
async def update_cost(
    cost_id: UUID,
    payload: CostUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CostResponse:
    row = await CostService(db, current_user).update_cost(
        cost_id,
        product_cost=payload.product_cost,
        packaging_cost=payload.packaging_cost,
        inbound_logistics_cost=payload.inbound_logistics_cost,
        additional_cost=payload.additional_cost,
        currency=payload.currency,
        comment=payload.comment,
    )
    return CostResponse.model_validate(row)


@router.get("/import/template")
async def download_cost_import_template(
    _current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Download the Excel template for bulk cost import."""
    try:
        path = cost_import_template_path()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cost import template is not available on the server",
        ) from exc
    encoded_name = quote(COST_IMPORT_TEMPLATE_FILENAME)
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=COST_IMPORT_TEMPLATE_FILENAME,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
        },
    )


@router.get("/import/template-info")
async def cost_import_template_info(
    _current_user: User = Depends(get_current_user),
) -> dict[str, str | bool]:
    """Debug info for template resolution (local/prod packaging)."""
    return cost_import_template_resolution()


@router.post("/import/preview", response_model=CostImportPreviewResponse)
async def preview_cost_import(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CostImportPreviewResponse:
    content = await file.read()
    return await CostService(db, current_user).preview_import(
        filename=file.filename or "costs.xlsx",
        content=content,
    )


@router.post("/import/v2", response_model=CostImportResultResponse, status_code=201)
async def import_costs_v2(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CostImportResultResponse:
    content = await file.read()
    return await CostService(db, current_user).bulk_import_v2(
        filename=file.filename or "costs.xlsx",
        content=content,
    )


@router.post("/import", response_model=list[CostResponse], status_code=201)
async def import_costs(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CostResponse]:
    content = await file.read()
    rows = await CostService(db, current_user).bulk_import(
        filename=file.filename or "costs.csv",
        content=content,
    )
    return [CostResponse.model_validate(row) for row in rows]


@router.get("/{cost_id}", response_model=CostResponse)
async def get_cost(
    cost_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CostResponse:
    row = await CostService(db, current_user).get_cost(cost_id)
    return CostResponse.model_validate(row)
