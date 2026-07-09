"""Read-only platform admin endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_platform_admin
from app.models.user import User
from app.schemas.admin import AdminUserListItem, PaginatedAdminUsersResponse
from app.services.admin_service import AdminService

router = APIRouter()


@router.get("/users", response_model=PaginatedAdminUsersResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
) -> PaginatedAdminUsersResponse:
    rows, total = await AdminService(db).list_users(skip=skip, limit=limit)
    return PaginatedAdminUsersResponse(
        items=[
            AdminUserListItem(
                email=row.email,
                role=row.role,
                is_active=row.is_active,
                created_at=row.created_at,
            )
            for row in rows
        ],
        page=AdminService.page_meta(total, skip, limit),
    )
