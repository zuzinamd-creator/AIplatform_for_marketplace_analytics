"""Operator and privileged action audit."""

from __future__ import annotations

from uuid import UUID, uuid4

from app.core.observability.context import get_correlation_id
from app.core.security_context import DispatchSession, TenantSession
from app.models.reliability import OperatorAuditEvent
from app.runtime.metrics import emit_runtime_metric
from sqlalchemy.ext.asyncio import AsyncSession


async def record_operator_action(
    db: AsyncSession,
    *,
    action_type: str,
    detail: str,
    actor_type: str = "operator",
    user_id: UUID | None = None,
    payload: dict | None = None,
) -> UUID:
    event_id = uuid4()
    event = OperatorAuditEvent(
        id=event_id,
        user_id=user_id,
        actor_type=actor_type,
        action_type=action_type,
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
        "operator_audit_action",
        action_type=action_type,
        actor_type=actor_type,
        user_id=str(user_id) if user_id else "global",
        event_id=str(event_id),
    )
    return event_id
