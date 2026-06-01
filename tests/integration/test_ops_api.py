"""Operational read-only API (tenant-scoped)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from app.core.security import create_access_token
from app.core.security_context import TenantSession
from app.models.etl.anomaly import EtlAnomaly, EtlAnomalySeverity, EtlAnomalyType, EtlParserStage
from app.models.inventory.integrity import SnapshotConsistencyCheck
from app.models.job import EtlJob, JobStatus
from app.models.report import Marketplace, Report, ReportType
from app.models.semantics.governance import SnapshotRebuildRequirement
from app.models.user import User
from app.operations.rebuild_orchestration import RebuildOrchestrationService
from app.services.semantics_invalidation_service import SemanticsInvalidationService
from httpx import AsyncClient


@pytest.mark.integration
async def test_ops_endpoints_tenant_scoped(
    api_client: AsyncClient,
    session_factory,
) -> None:
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"ops-{user_id}@example.com",
        hashed_password="not-used",
        is_active=True,
    )
    headers = {"Authorization": f"Bearer {create_access_token(user_id)}"}

    report_id = uuid4()
    async with session_factory() as session:
        async with session.begin():
            session.add(user)
            await session.flush()
        async with TenantSession.transaction(session, user.id):
            session.add(
                Report(
                    id=report_id,
                    user_id=user.id,
                    marketplace=Marketplace.WILDBERRIES,
                    report_type=ReportType.SALES,
                    original_filename="ops.csv",
                    file_path="reports/ops.csv",
                    file_checksum=f"ops-{uuid4()}",
                )
            )
            await SemanticsInvalidationService(session, user.id).request_rebuild(
                semantics_version="1.0",
                reason="ops integration test",
            )
            session.add(
                EtlAnomaly(
                    user_id=user.id,
                    report_id=report_id,
                    source_file_name="ops.csv",
                    severity=EtlAnomalySeverity.WARNING,
                    anomaly_type=EtlAnomalyType.VALIDATION_WARNING,
                    parser_stage=EtlParserStage.PERSIST,
                    raw_payload={},
                    error_message="test anomaly",
                )
            )
            session.add(
                SnapshotConsistencyCheck(
                    user_id=user.id,
                    snapshot_date=date(2026, 1, 15),
                    sku="SKU-OPS",
                    warehouse_name="WH-1",
                    ledger_hash="abc",
                    snapshot_hash="def",
                    semantics_version="1.0",
                    is_consistent=False,
                    mismatch_details={"test": True},
                )
            )
            session.add(
                EtlJob(
                    user_id=user.id,
                    report_id=report_id,
                    job_type="etl_process_report",
                    status=JobStatus.DEAD_LETTER,
                    idempotency_key=f"ops-job-{uuid4()}",
                    file_path="reports/ops.csv",
                    marketplace="wildberries",
                    report_type="sales",
                    original_filename="ops.csv",
                    report_created_at=datetime.now(UTC),
                    attempt_count=3,
                    max_attempts=3,
                    last_error="synthetic dead letter",
                )
            )
            await session.flush()
            from sqlalchemy import select

            result = await session.execute(select(SnapshotRebuildRequirement))
            req = result.scalars().first()
            assert req is not None
            orch = RebuildOrchestrationService(session, user.id)
            await orch.mark_running(req)
            await orch.mark_succeeded(req)

    rebuilds = await api_client.get("/api/v1/ops/rebuilds", headers=headers)
    assert rebuilds.status_code == 200
    body = rebuilds.json()
    assert body["page"]["total"] >= 1
    assert body["items"][0]["orchestration_status"] == "succeeded"

    anomalies = await api_client.get("/api/v1/ops/anomalies", headers=headers)
    assert anomalies.status_code == 200
    assert anomalies.json()["page"]["total"] >= 1

    drift = await api_client.get(
        "/api/v1/ops/drift-checks",
        headers=headers,
        params={"consistent_only": False},
    )
    assert drift.status_code == 200
    assert drift.json()["items"][0]["is_consistent"] is False

    queue = await api_client.get("/api/v1/ops/queue", headers=headers)
    assert queue.status_code == 200
    assert "status_counts" in queue.json()

    dead = await api_client.get("/api/v1/ops/dead-letters", headers=headers)
    assert dead.status_code == 200
    assert dead.json()["page"]["total"] >= 1

    semantics = await api_client.get("/api/v1/ops/semantics-status", headers=headers)
    assert semantics.status_code == 200
    assert any(v["version"] == "1.0" for v in semantics.json()["versions"])


@pytest.mark.integration
async def test_ops_rebuild_status_transitions(session_factory) -> None:
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"orch-{user_id}@example.com",
        hashed_password="x",
        is_active=True,
    )
    async with session_factory() as session:
        async with session.begin():
            session.add(user)
        async with TenantSession.transaction(session, user_id):
            row = await SemanticsInvalidationService(session, user_id).request_rebuild(
                semantics_version="1.0",
                reason="transition test",
            )
            orch = RebuildOrchestrationService(session, user_id)
            await orch.mark_queued(row)
            await orch.mark_running(row)
            assert row.orchestration_status.value == "running"
            assert row.attempt_count == 1
            await orch.mark_failed(row, error="transient")
            assert row.orchestration_status.value == "deferred"
            assert row.next_eligible_at is not None
