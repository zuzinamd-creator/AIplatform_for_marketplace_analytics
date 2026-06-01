from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models.semantics.governance import (
    RebuildMode,
    RebuildOrchestrationStatus,
    SnapshotRebuildRequirement,
)
from app.operations.rebuild_orchestration import (
    RebuildPriority,
    compute_next_eligible_at,
    is_eligible_for_dispatch,
    select_fair_batch,
)


def _requirement(**kwargs: object) -> SnapshotRebuildRequirement:
    defaults = {
        "id": uuid4(),
        "user_id": uuid4(),
        "semantics_version": "1.0",
        "reason": "test",
        "requires_rebuild": True,
        "orchestration_status": RebuildOrchestrationStatus.PENDING,
        "rebuild_mode": RebuildMode.INCREMENTAL,
        "priority": RebuildPriority.DEFAULT,
        "attempt_count": 0,
        "max_attempts": 3,
        "last_error": None,
        "last_attempted_at": None,
        "next_eligible_at": None,
        "started_at": None,
        "completed_at": None,
        "created_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    return SnapshotRebuildRequirement(**defaults)  # type: ignore[arg-type]


def test_compute_next_eligible_at_backoff() -> None:
    t0 = compute_next_eligible_at(0, base_delay_seconds=30)
    t2 = compute_next_eligible_at(2, base_delay_seconds=30)
    assert t2 > t0


def test_is_eligible_respects_next_eligible_at() -> None:
    future = datetime.now(UTC) + timedelta(hours=1)
    row = _requirement(
        next_eligible_at=future,
        orchestration_status=RebuildOrchestrationStatus.DEFERRED,
    )
    assert is_eligible_for_dispatch(row) is False


def test_select_fair_batch_caps_per_tenant() -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    rows = [
        _requirement(user_id=tenant_a, priority=10),
        _requirement(user_id=tenant_a, priority=20),
        _requirement(user_id=tenant_b, priority=15),
    ]
    picked = select_fair_batch(rows, limit=3)
    assert len(picked) == 2
    assert {r.user_id for r in picked} == {tenant_a, tenant_b}
