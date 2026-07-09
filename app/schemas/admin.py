"""Admin panel schemas (Phase 9.2C — read-only)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr

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
