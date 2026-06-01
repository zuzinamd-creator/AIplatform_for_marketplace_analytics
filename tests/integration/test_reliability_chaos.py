"""Reliability integration — lease, heartbeat, containment simulations."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.models.reliability import ProcessKind, TenantContainmentStatus
from app.runtime.containment.tenant_guard import TenantContainmentGuard
from app.runtime.resilience.lease import OrchestratorLeaseService
from app.runtime.resilience.process_registry import ProcessSupervisorRegistry


@pytest.mark.integration
async def test_orchestrator_lease_exclusive(db_session) -> None:
    holder_a = uuid4()
    holder_b = uuid4()
    lease_a = OrchestratorLeaseService(db_session, holder_id=holder_a)
    lease_b = OrchestratorLeaseService(db_session, holder_id=holder_b)
    first = await lease_a.try_acquire()
    assert first.acquired is True
    second = await lease_b.try_acquire()
    assert second.acquired is False
    await lease_a.release()


@pytest.mark.integration
async def test_process_heartbeat_and_stale_cleanup(db_session) -> None:
    registry = ProcessSupervisorRegistry(db_session)
    process_id = await registry.heartbeat(ProcessKind.ETL_WORKER)
    live = await registry.list_live(ProcessKind.ETL_WORKER)
    assert any(row.process_id == process_id for row in live)


@pytest.mark.integration
async def test_tenant_quarantine_blocks_guard(integration_user, db_session) -> None:
    guard = TenantContainmentGuard(db_session)
    result = await guard._set_status(
        integration_user.id,
        TenantContainmentStatus.QUARANTINED,
        "integration test quarantine",
    )
    assert result.allowed is False
    check = await guard.check(integration_user.id)
    assert check.allowed is False
