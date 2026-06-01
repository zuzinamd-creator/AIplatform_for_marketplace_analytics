from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security_context import TenantSession
from app.models.workflow import SellerWorkflowEvent
from app.schemas.workflow import WorkflowEventCreateRequest
from app.services.base import TenantScopedService


class WorkflowService(TenantScopedService):
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        super().__init__(db, user_id=user_id)
        self._uid = user_id

    async def add_event(self, body: WorkflowEventCreateRequest) -> SellerWorkflowEvent:
        async with TenantSession.transaction(self.db, self._uid):
            row = SellerWorkflowEvent(
                id=uuid.uuid4(),
                user_id=self._uid,
                recommendation_id=body.recommendation_id,
                event_type=body.event_type,
                note=body.note,
                reminder_at=body.reminder_at,
                metadata_json=body.metadata_json,
            )
            self.db.add(row)
            await self.db.flush()
            return row

    async def history(
        self,
        *,
        recommendation_id: UUID | None,
        limit: int = 100,
    ) -> list[SellerWorkflowEvent]:
        stmt = select(SellerWorkflowEvent).where(SellerWorkflowEvent.user_id == self._uid)
        if recommendation_id is not None:
            stmt = stmt.where(SellerWorkflowEvent.recommendation_id == recommendation_id)
        stmt = stmt.order_by(desc(SellerWorkflowEvent.created_at)).limit(limit)
        res = await self.execute_with_rls(stmt)
        return list(res.scalars().all())

    async def due_reminders(self, *, now: datetime, limit: int = 50) -> list[SellerWorkflowEvent]:
        stmt = (
            select(SellerWorkflowEvent)
            .where(SellerWorkflowEvent.user_id == self._uid)
            .where(SellerWorkflowEvent.reminder_at.is_not(None))
            .where(SellerWorkflowEvent.reminder_at <= now)
            .order_by(SellerWorkflowEvent.reminder_at.asc())
            .limit(limit)
        )
        res = await self.execute_with_rls(stmt)
        return list(res.scalars().all())

