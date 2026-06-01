"""Background supervisor heartbeat loop for long-running processes."""

from __future__ import annotations

import asyncio
import contextlib
from uuid import UUID

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.reliability import ProcessKind
from app.runtime.resilience.process_registry import ProcessSupervisorRegistry


class ProcessSupervisor:
    def __init__(
        self,
        *,
        process_kind: ProcessKind,
        process_id: UUID | None = None,
        shutdown: asyncio.Event | None = None,
    ) -> None:
        self.process_kind = process_kind
        self.process_id = process_id
        self._shutdown = shutdown or asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._holder_id: UUID | None = process_id

    async def _loop(self) -> None:
        interval = float(settings.reliability_process_heartbeat_interval_seconds)
        while not self._shutdown.is_set():
            try:
                async with SessionLocal() as db:
                    registry = ProcessSupervisorRegistry(db, process_id=self._holder_id)
                    self._holder_id = await registry.heartbeat(self.process_kind)
                    if self.process_kind == ProcessKind.ORCHESTRATOR:
                        await registry.cleanup_stale()
            except Exception:
                pass
            try:
                await asyncio.wait_for(self._shutdown.wait(), timeout=interval)
            except TimeoutError:
                pass

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._shutdown.set()
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
