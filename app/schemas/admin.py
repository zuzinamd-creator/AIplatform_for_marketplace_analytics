"""Admin panel schemas (Phase 9.2C — read-only)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.auth import UserRole
from app.schemas.ops import PageMeta

AdminUserRole = UserRole


class AdminUserListItem(BaseModel):
    model_config = ConfigDict(strict=True)

    email: EmailStr
    role: Literal["seller", "platform_admin"]
    is_active: bool
    created_at: datetime


class PaginatedAdminUsersResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    items: list[AdminUserListItem]
    page: PageMeta


InviteStatus = Literal["pending", "used", "expired", "revoked"]


class AdminInviteCreateRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    email: EmailStr
    expires_in_hours: int | None = Field(default=None, ge=1, le=720)


class AdminInviteCreateResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    email: EmailStr
    role: Literal["seller"]
    status: InviteStatus
    expires_at: datetime
    created_at: datetime
    invite_link: str = Field(min_length=1, max_length=2048)


class AdminInviteListItem(BaseModel):
    model_config = ConfigDict(strict=True)

    id: UUID
    email: EmailStr
    role: Literal["seller", "platform_admin"]
    status: InviteStatus
    expires_at: datetime
    created_at: datetime


class PaginatedAdminInvitesResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    items: list[AdminInviteListItem]
    page: PageMeta
