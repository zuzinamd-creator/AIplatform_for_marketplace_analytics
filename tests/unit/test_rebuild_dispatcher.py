"""Unit tests for rebuild dispatch selection and defer-busy orchestration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.semantics.governance import RebuildOrchestrationStatus
from app.operations.rebuild_orchestration import (
    RebuildOrchestrationService,
    is_eligible_for_dispatch,
)
from tests.unit.test_rebuild_orchestration import _requirement


@pytest.mark.asyncio
async def test_mark_deferred_lock_busy_undoes_attempt() -> None:
    row = _requirement(attempt_count=1, orchestration_status=RebuildOrchestrationStatus.RUNNING)
    orch = RebuildOrchestrationService(MagicMock(), row.user_id)
    await orch.mark_deferred_lock_busy(row, defer_seconds=30)
    assert row.attempt_count == 0
    assert row.orchestration_status == RebuildOrchestrationStatus.DEFERRED
    assert row.next_eligible_at is not None


@pytest.mark.asyncio
async def test_dispatcher_skips_ineligible() -> None:
    from app.runtime.rebuild_dispatcher import RebuildDispatcher

    db = AsyncMock()
    dispatcher = RebuildDispatcher(db)

    with patch.object(dispatcher, "_select_requirement_id", AsyncMock(return_value=None)):
        result = await dispatcher.dispatch_once()
    assert result.dispatched is False
    assert result.outcome == "idle"


def test_failed_status_eligible_when_under_max_attempts() -> None:
    row = _requirement(
        orchestration_status=RebuildOrchestrationStatus.FAILED,
        attempt_count=2,
        max_attempts=3,
    )
    assert is_eligible_for_dispatch(row) is True


def test_running_not_eligible() -> None:
    row = _requirement(orchestration_status=RebuildOrchestrationStatus.RUNNING)
    assert is_eligible_for_dispatch(row) is False
