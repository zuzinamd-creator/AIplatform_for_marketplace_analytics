"""Platform admin read-only services (Phase 9.2C)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.ops import PageMeta


class AdminService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def page_meta(total: int, skip: int, limit: int) -> PageMeta:
        return PageMeta(total=total, skip=skip, limit=limit)

    async def list_users(self, *, skip: int = 0, limit: int = 50) -> tuple[list[User], int]:
        count_stmt = select(func.count()).select_from(User)
        total = int((await self.db.execute(count_stmt)).scalar_one())

        stmt = (
            select(User)
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total
