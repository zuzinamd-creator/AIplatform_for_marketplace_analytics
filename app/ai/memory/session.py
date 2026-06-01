"""Bounded session memory with audit trail."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.sanitization import sanitize_user_text
from app.core.config import settings
from app.core.security_context import TenantSession
from app.core.tenant_context import set_current_user_context, set_queue_role_context
from app.models.ai_session import AISessionTurn


class AISessionMemory:
    """Non-authoritative bounded memory per tenant session."""

    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    @asynccontextmanager
    async def _tenant_scope(self) -> AsyncGenerator[None]:
        if self.db.in_transaction():
            await set_queue_role_context(self.db, False)
            await set_current_user_context(self.db, self.user_id)
            yield
        else:
            async with TenantSession.transaction(self.db, self.user_id):
                yield

    async def append_turn(
        self,
        *,
        session_id: UUID,
        role: str,
        content: str,
        run_id: UUID | None = None,
    ) -> None:
        sanitized = sanitize_user_text(content, max_length=2000)
        turn = AISessionTurn(
            user_id=self.user_id,
            session_id=session_id,
            run_id=run_id,
            role=role[:16],
            content=sanitized,
            token_estimate=max(1, len(sanitized) // 4),
        )
        async with self._tenant_scope():
            self.db.add(turn)
            await self.db.flush()
            await self._trim_old_turns(session_id)

    async def load_recent(self, session_id: UUID) -> list[tuple[str, str]]:
        async with self._tenant_scope():
            result = await self.db.execute(
                select(AISessionTurn)
                .where(
                    AISessionTurn.user_id == self.user_id,
                    AISessionTurn.session_id == session_id,
                )
                .order_by(AISessionTurn.created_at.desc())
                .limit(settings.ai_memory_max_turns)
            )
            rows = list(reversed(result.scalars().all()))
        return [(row.role, row.content) for row in rows]

    async def _trim_old_turns(self, session_id: UUID) -> None:
        max_turns = settings.ai_memory_max_turns
        count = (
            await self.db.execute(
                select(func.count())
                .select_from(AISessionTurn)
                .where(
                    AISessionTurn.user_id == self.user_id,
                    AISessionTurn.session_id == session_id,
                )
            )
        ).scalar_one()
        if int(count) <= max_turns:
            return
        excess = int(count) - max_turns
        oldest = await self.db.execute(
            select(AISessionTurn.id)
            .where(
                AISessionTurn.user_id == self.user_id,
                AISessionTurn.session_id == session_id,
            )
            .order_by(AISessionTurn.created_at.asc())
            .limit(excess)
        )
        for row_id in oldest.scalars():
            row = await self.db.get(AISessionTurn, row_id)
            if row is not None:
                await self.db.delete(row)


def new_session_id() -> UUID:
    return uuid4()
