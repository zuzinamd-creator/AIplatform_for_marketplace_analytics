from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security_context import TenantSession


class TenantScopedService:
    """Base service configuring tenant RLS context only."""

    def __init__(self, db: AsyncSession, user_id: UUID | None = None):
        self.db = db
        self.user_id = user_id

    @asynccontextmanager
    async def _rls_transaction(self) -> AsyncIterator[None]:
        if self.user_id is None:
            raise ValueError("user_id is required for tenant-scoped transactions")
        async with TenantSession.transaction(self.db, self.user_id):
            yield

    async def execute_with_rls(self, statement: Select):
        async with self._rls_transaction():
            return await self.db.execute(statement)
