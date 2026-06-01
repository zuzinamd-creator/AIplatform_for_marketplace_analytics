"""Persist autonomous action audit events."""

from __future__ import annotations

from uuid import UUID, uuid4

from app.core.observability.context import get_correlation_id
from app.core.security_context import DispatchSession, TenantSession
from app.models.runtime_autonomy import RuntimeAutonomyEvent
from app.runtime.metrics import emit_runtime_metric
from sqlalchemy.ext.asyncio import AsyncSession


async def record_autonomy_event(
    db: AsyncSession,
    *,
    action_type: str,
    detail: str,
    user_id: UUID | None = None,
    reversible: bool = True,
    payload: dict | None = None,
) -> UUID:
    event_id = uuid4()
    event = RuntimeAutonomyEvent(
        id=event_id,
        user_id=user_id,
        action_type=action_type,
        reversible=reversible,
        detail=detail[:4000],
        payload=payload,
        correlation_id=get_correlation_id(),
    )
    if user_id is not None:
        async with TenantSession.transaction(db, user_id):
            db.add(event)
            await db.flush()
    else:
        async with DispatchSession.transaction(db):
            db.add(event)
            await db.flush()

    emit_runtime_metric(
        "runtime_autonomy_action",
        action_type=action_type,
        user_id=str(user_id) if user_id else "global",
        reversible=reversible,
        event_id=str(event_id),
    )
    return event_id
