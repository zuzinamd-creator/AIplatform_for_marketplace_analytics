"""
Security context boundaries for PostgreSQL RLS.

- TenantSession: API/worker business data under app.current_user_id
- QueueSession: etl_jobs broker only (app.queue_role), no business table access
- SystemSession: Alembic migrations and internal maintenance only
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import (
    set_bypass_rls_context,
    set_current_user_context,
    set_queue_role_context,
)

# Session.info key: tenant RLS already bound for this user in the open transaction
# (Phase 9.18-D — avoid repeated set_config round-trips inside one dashboard branch).
TENANT_USER_INFO_KEY = "marketplace_tenant_user_id"


def tenant_context_bound(db: AsyncSession, user_id: UUID) -> bool:
    return db.info.get(TENANT_USER_INFO_KEY) == str(user_id)


async def bind_tenant_context(db: AsyncSession, user_id: UUID) -> None:
    """Apply RLS GUCs once and mark the session for reuse within this transaction."""
    await set_queue_role_context(db, False)
    await set_current_user_context(db, user_id)
    db.info[TENANT_USER_INFO_KEY] = str(user_id)


class TenantSession:
    """Tenant-scoped DB access. Never enables RLS bypass or queue role."""

    @staticmethod
    @asynccontextmanager
    async def transaction(db: AsyncSession, user_id: UUID) -> AsyncGenerator[None]:
        if db.in_transaction():
            if tenant_context_bound(db, user_id):
                # Already in a tenant transaction for this user — no nested savepoint / set_config.
                yield
                return
            async with db.begin_nested():
                await bind_tenant_context(db, user_id)
                yield
            return
        async with db.begin():
            await bind_tenant_context(db, user_id)
            yield


class QueueSession:
    """
    Queue-broker context: limited to etl_jobs via RLS queue_role policy.

    Must not be used for reports/products/metrics access.
    """

    @staticmethod
    @asynccontextmanager
    async def transaction(db: AsyncSession) -> AsyncGenerator[None]:
        async with db.begin():
            await set_bypass_rls_context(db, False)
            await set_queue_role_context(db, True)
            yield


class DispatchSession:
    """
    Cross-tenant orchestration **read** context (queue_role on RLS tables).

    Use only to list/claim rebuild requirements and queue metrics.
    All tenant mutations must run in TenantSession with the row's user_id.
    """

    @staticmethod
    @asynccontextmanager
    async def transaction(db: AsyncSession) -> AsyncGenerator[None]:
        async with db.begin():
            await set_bypass_rls_context(db, False)
            await set_queue_role_context(db, True)
            yield


class SystemSession:
    """Maintenance-only: Alembic migrations and rare internal ops."""

    @staticmethod
    @asynccontextmanager
    async def transaction(db: AsyncSession) -> AsyncGenerator[None]:
        async with db.begin():
            await set_queue_role_context(db, False)
            await set_bypass_rls_context(db, True)
            yield
