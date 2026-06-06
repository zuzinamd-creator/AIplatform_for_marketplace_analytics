"""Record seller auth audit events (password change / reset)."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.observability.context import get_correlation_id
from app.core.tenant_context import set_current_user_context, set_queue_role_context
from app.models.auth_audit import AuthAuditEvent, AuthAuditEventType


async def record_auth_audit(
    db: AsyncSession,
    *,
    user_id: UUID,
    event_type: AuthAuditEventType | str,
    detail: str,
    payload: dict | None = None,
) -> UUID:
    """Append audit row in the caller's transaction (sets RLS tenant context)."""
    event_id = uuid4()
    await set_queue_role_context(db, False)
    await set_current_user_context(db, user_id)
    event = AuthAuditEvent(
        id=event_id,
        user_id=user_id,
        event_type=str(event_type),
        detail=detail[:4000],
        payload=payload,
        correlation_id=get_correlation_id(),
    )
    db.add(event)
    await db.flush()
    return event_id
