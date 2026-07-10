"""Platform admin endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_platform_admin
from app.models.user import User
from app.schemas.admin import (
    AdminInviteCreateRequest,
    AdminInviteCreateResponse,
    AdminInviteListItem,
    AdminUserListItem,
    PaginatedAdminInvitesResponse,
    PaginatedAdminUsersResponse,
)
from app.services.admin_service import AdminService
from app.services.invite_service import InviteService

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


@router.get("/invites", response_model=PaginatedAdminInvitesResponse)
async def list_invites(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_platform_admin),
) -> PaginatedAdminInvitesResponse:
    service = InviteService(db)
    rows, total = await service.list_invites(skip=skip, limit=limit)
    return PaginatedAdminInvitesResponse(
        items=[
            AdminInviteListItem(
                id=row.id,
                email=row.email,
                role=row.role,
                status=service.derive_status(row),
                expires_at=row.expires_at,
                created_at=row.created_at,
            )
            for row in rows
        ],
        page=service.page_meta(total, skip, limit),
    )


@router.post("/invites", response_model=AdminInviteCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    body: AdminInviteCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_platform_admin),
) -> AdminInviteCreateResponse:
    service = InviteService(db)
    invite, raw_token = await service.create_invite(
        admin=admin,
        email=str(body.email),
        expires_in_hours=body.expires_in_hours,
    )
    return AdminInviteCreateResponse(
        email=invite.email,
        role="seller",
        status=service.derive_status(invite),
        expires_at=invite.expires_at,
        created_at=invite.created_at,
        invite_link=service.build_invite_link(raw_token),
    )


@router.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite(
    invite_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_platform_admin),
) -> None:
    await InviteService(db).revoke_invite(invite_id=invite_id, admin=admin)
