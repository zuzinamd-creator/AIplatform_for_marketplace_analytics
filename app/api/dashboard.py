"""Aggregated dashboard endpoint (single round-trip for the main panel)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.report import Marketplace
from app.models.user import User
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard_service import DashboardService

router = APIRouter()


def _marketplace(value: str) -> Marketplace:
    return Marketplace(value.lower())


@router.get("/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(
    marketplace: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    compare_start: date | None = Query(None),
    compare_end: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardSummaryResponse:
    return await DashboardService(db, current_user).summary(
        marketplace=_marketplace(marketplace),
        start=start,
        end=end,
        compare_start=compare_start,
        compare_end=compare_end,
    )
