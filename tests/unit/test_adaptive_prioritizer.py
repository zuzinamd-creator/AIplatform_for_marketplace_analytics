"""Adaptive rebuild prioritization."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models.semantics.governance import RebuildMode, RebuildOrchestrationStatus
from app.operations.rebuild_orchestration import RebuildPriority
from app.runtime.adaptive.prioritizer import AdaptiveRebuildPrioritizer
from tests.unit.test_rebuild_orchestration import _requirement


def test_starvation_boost_orders_older_tenant_first() -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    old = datetime.now(UTC) - timedelta(hours=3)
    rows = [
        _requirement(
            user_id=tenant_b,
            priority=RebuildPriority.DEFAULT,
            created_at=datetime.now(UTC),
        ),
        _requirement(
            user_id=tenant_a,
            priority=RebuildPriority.DEFAULT,
            created_at=old,
            orchestration_status=RebuildOrchestrationStatus.PENDING,
            rebuild_mode=RebuildMode.INCREMENTAL,
        ),
    ]
    ordered = AdaptiveRebuildPrioritizer().adjust(rows)
    assert ordered[0].user_id == tenant_a
