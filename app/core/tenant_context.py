from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_current_user_context(db: AsyncSession, user_id: UUID) -> None:
    """Set transaction-local tenant context for RLS."""
    await db.execute(
        text("SELECT set_config('app.current_user_id', :user_id, true)"),
        {"user_id": str(user_id)},
    )


async def set_queue_role_context(db: AsyncSession, enabled: bool) -> None:
    """
    Enable queue-broker role for etl_jobs-only operations.

    Does NOT grant access to business tables (reports, products, etc.).
    """
    await db.execute(
        text("SELECT set_config('app.queue_role', :enabled, true)"),
        {"enabled": "true" if enabled else "false"},
    )


async def set_bypass_rls_context(db: AsyncSession, enabled: bool) -> None:
    """Alembic / internal maintenance only."""
    await db.execute(
        text("SELECT set_config('app.bypass_rls', :enabled, true)"),
        {"enabled": "true" if enabled else "false"},
    )
