"""Seller workflow persistence endpoints (tenant-scoped, additive)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.workflow import (
    WorkflowEventCreateRequest,
    WorkflowEventResponse,
    WorkflowHistoryResponse,
)
from app.services.workflow_service import WorkflowService

router = APIRouter()


@router.post("/events", response_model=WorkflowEventResponse)
async def create_event(
    body: WorkflowEventCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkflowEventResponse:
    row = await WorkflowService(db, current_user.id).add_event(body)
    return WorkflowEventResponse.model_validate(row)


@router.get("/history", response_model=WorkflowHistoryResponse)
async def workflow_history(
    recommendation_id: UUID | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkflowHistoryResponse:
    items = await WorkflowService(db, current_user.id).history(recommendation_id=recommendation_id, limit=limit)
    return WorkflowHistoryResponse(
        recommendation_id=recommendation_id,
        items=[WorkflowEventResponse.model_validate(i) for i in items],
    )


@router.get("/reminders/due", response_model=list[WorkflowEventResponse])
async def due_reminders(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WorkflowEventResponse]:
    now = datetime.now(UTC)
    items = await WorkflowService(db, current_user.id).due_reminders(now=now, limit=limit)
    return [WorkflowEventResponse.model_validate(i) for i in items]

