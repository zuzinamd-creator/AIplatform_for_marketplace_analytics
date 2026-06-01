"""Integration tests for runtime rebuild dispatch."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from app.core.security_context import TenantSession
from app.models.inventory import InventoryLedgerEntry
from app.models.inventory.enums import InventoryOperationType
from app.models.report import Marketplace, Report, ReportStatus, ReportType
from app.models.semantics.governance import RebuildOrchestrationStatus, SnapshotRebuildRequirement
from app.models.user import User
from app.runtime.rebuild_dispatcher import RebuildDispatcher
from app.services.semantics_invalidation_service import SemanticsInvalidationService
from sqlalchemy import select


async def _seed_tenant_ledger(session, user_id) -> None:
    report_id = uuid4()
    session.add(
        Report(
            id=report_id,
            user_id=user_id,
            marketplace=Marketplace.WILDBERRIES,
            report_type=ReportType.SALES,
            original_filename="orch.csv",
            file_path="reports/orch.csv",
            file_checksum=f"orch-{uuid4()}",
            status=ReportStatus.PROCESSED,
        )
    )
    await session.flush()
    payload = {"source": "orch-test"}
    session.add(
        InventoryLedgerEntry(
            user_id=user_id,
            report_id=report_id,
            operation_date=date(2026, 1, 10),
            sku="SKU-ORCH",
            nm_id=None,
            warehouse_name="WH-1",
            operation_type=InventoryOperationType.INBOUND,
            quantity_delta=5,
            cost_per_unit=Decimal("10"),
            sale_price_per_unit=None,
            total_cost_delta=Decimal("50"),
            total_sale_delta=Decimal("0"),
            source_row_id="row-1",
            semantics_version="1.0",
            canonical_payload=payload,
            raw_payload=payload,
        )
    )


@pytest.mark.integration
async def test_dispatcher_completes_pending_requirement(session_factory) -> None:
    user_id = uuid4()
    async with session_factory() as session:
        async with session.begin():
            session.add(
                User(
                    id=user_id,
                    email=f"orch-{user_id}@example.com",
                    hashed_password="x",
                    is_active=True,
                )
            )

        async with TenantSession.transaction(session, user_id):
            await _seed_tenant_ledger(session, user_id)
            await SemanticsInvalidationService(session, user_id).request_rebuild(
                semantics_version="1.0",
                reason="orchestration integration test",
            )

        dispatcher = RebuildDispatcher(session)
        result = await dispatcher.dispatch_once()
        assert result.dispatched is True
        assert result.outcome == "succeeded"

        async with TenantSession.transaction(session, user_id):
            row = (
                await session.execute(
                    select(SnapshotRebuildRequirement).where(
                        SnapshotRebuildRequirement.user_id == user_id,
                    )
                )
            ).scalar_one()
            assert row.orchestration_status == RebuildOrchestrationStatus.SUCCEEDED
            assert row.requires_rebuild is False
