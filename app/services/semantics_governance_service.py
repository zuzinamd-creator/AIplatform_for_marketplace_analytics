"""Load semantics lifecycle registry from DB into process cache."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.semantics.governance_policy import (
    SemanticsLifecycleRecord,
    SemanticsLifecycleStatus,
    set_lifecycle_cache,
)
from app.models.semantics.governance import SemanticsLifecycleVersion


class SemanticsGovernanceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def refresh_cache(self) -> dict[str, SemanticsLifecycleRecord]:
        result = await self.db.execute(select(SemanticsLifecycleVersion))
        records: dict[str, SemanticsLifecycleRecord] = {}
        for row in result.scalars().all():
            records[row.version] = SemanticsLifecycleRecord(
                version=row.version,
                status=SemanticsLifecycleStatus(row.status.value),
                supported_for_rebuild=row.supported_for_rebuild,
                supported_for_ingest=row.supported_for_ingest,
            )
        set_lifecycle_cache(records)
        return records
