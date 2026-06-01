from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.queue.types import ClaimedJobRecord, EnqueuePayload, RecoveryRecord
from app.models.job import EtlJob


class QueueBackend(Protocol):
    """Storage-agnostic job queue contract."""

    def __init__(self, db: AsyncSession) -> None: ...

    async def enqueue(self, payload: EnqueuePayload) -> EtlJob: ...

    async def claim(self) -> ClaimedJobRecord | None: ...

    async def ack(self, job_id: str) -> None: ...

    async def fail(
        self,
        job_id: str,
        *,
        error_message: str,
        attempt_count: int,
        max_attempts: int,
        poison: bool = False,
    ) -> None: ...

    async def requeue(self, job_id: str) -> None: ...

    async def recover_stale(self) -> list[RecoveryRecord]: ...

    async def heartbeat(self, job_id: str) -> None: ...
