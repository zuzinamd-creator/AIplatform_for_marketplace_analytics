"""PostgreSQL session timeouts for ETL transactions."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession


def is_lock_timeout_error(exc: BaseException) -> bool:
    """True when PostgreSQL aborted the statement due to lock_timeout."""
    message = str(exc).lower()
    if "lock timeout" in message or "canceling statement due to lock timeout" in message:
        return True
    orig = getattr(exc, "orig", None)
    if orig is not None:
        pgcode = getattr(orig, "pgcode", None) or getattr(orig, "sqlstate", None)
        if pgcode == "55P03":
            return True
    if isinstance(exc, DBAPIError) and exc.orig is not None:
        return is_lock_timeout_error(exc.orig)
    return False


async def set_local_lock_timeout(db: AsyncSession, *, timeout_ms: int) -> None:
    """SET LOCAL lock_timeout — fail fast on row lock waits (multi-worker aggregates)."""
    if timeout_ms <= 0:
        return
    ms = int(timeout_ms)
    await db.execute(text(f"SET LOCAL lock_timeout = '{ms}ms'"))
