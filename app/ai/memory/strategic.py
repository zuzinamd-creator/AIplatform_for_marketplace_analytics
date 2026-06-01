"""Strategic memory — long-lived tenant analytical context."""

from __future__ import annotations

import hashlib
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security_context import TenantSession
from app.models.ai_intelligence import AIStrategicMemory


class StrategicMemoryStore:
    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def remember(
        self,
        *,
        memory_key: str,
        content: str,
        semantics_version: str,
        source_run_id: UUID | None = None,
        metadata: dict | None = None,
    ) -> AIStrategicMemory | None:
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        async with TenantSession.transaction(self.db, self.user_id):
            existing = (
                await self.db.execute(
                    select(AIStrategicMemory).where(
                        AIStrategicMemory.user_id == self.user_id,
                        AIStrategicMemory.memory_key == memory_key,
                        AIStrategicMemory.content_hash == content_hash,
                    )
                )
            ).scalar_one_or_none()
            if existing is not None:
                return None
            row = AIStrategicMemory(
                user_id=self.user_id,
                memory_key=memory_key,
                content=content[:8000],
                semantics_version=semantics_version,
                source_run_id=source_run_id,
                content_hash=content_hash,
                metadata_json=metadata,
            )
            self.db.add(row)
            await self.db.flush()
            return row

    async def recall(self, memory_key: str, *, limit: int = 5) -> list[AIStrategicMemory]:
        async with TenantSession.transaction(self.db, self.user_id):
            rows = (
                await self.db.execute(
                    select(AIStrategicMemory)
                    .where(
                        AIStrategicMemory.user_id == self.user_id,
                        AIStrategicMemory.memory_key == memory_key,
                    )
                    .order_by(AIStrategicMemory.created_at.desc())
                    .limit(limit)
                )
            ).scalars().all()
        return list(rows)
