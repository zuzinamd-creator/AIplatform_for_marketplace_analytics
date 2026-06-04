from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.core.queue.types import ClaimedJobRecord
from app.etl import worker


def test_job_heartbeat_scope_keeps_task_alive_during_work(monkeypatch: pytest.MonkeyPatch) -> None:
    started = asyncio.Event()
    finished = asyncio.Event()

    async def fake_loop(job_id: str, user_id, interval=None) -> None:  # noqa: ARG001
        started.set()
        try:
            while True:
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            finished.set()
            raise

    monkeypatch.setattr(worker, "_heartbeat_loop", fake_loop)

    job_id = uuid4()
    user_id = uuid4()
    worker._current_job = ClaimedJobRecord(
        job_id=job_id,
        report_id=uuid4(),
        user_id=user_id,
        report_created_at=datetime.now(UTC),
        marketplace="wildberries",
        report_type="sales",
        original_filename="t.xlsx",
        file_path="/tmp/t.xlsx",
        attempt_count=1,
        max_attempts=3,
        idempotency_key="k",
        visibility_timeout_seconds=1800,
    )

    async def run_scope() -> None:
        async with worker._job_heartbeat_scope(str(job_id), user_id):
            await asyncio.wait_for(started.wait(), timeout=1.0)
            await asyncio.sleep(0.05)

    try:
        asyncio.run(run_scope())
        asyncio.run(asyncio.wait_for(finished.wait(), timeout=1.0))
    finally:
        worker._current_job = None
