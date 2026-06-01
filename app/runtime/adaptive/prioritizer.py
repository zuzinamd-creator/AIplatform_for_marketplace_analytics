"""Adaptive rebuild prioritization — backlog and starvation aware."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.models.semantics.governance import SnapshotRebuildRequirement
from app.operations.rebuild_orchestration import RebuildPriority


@dataclass(frozen=True)
class AdaptivePriorityAdjustment:
    requirement_id: UUID
    original_priority: int
    adjusted_priority: int
    reason: str


class AdaptiveRebuildPrioritizer:
    """
    Computes sort keys without hidden DB writes.

    Starved tenants (oldest created_at in batch) receive a priority boost (lower number).
    """

    def adjust(
        self,
        rows: list[SnapshotRebuildRequirement],
        *,
        starvation_boost: int = 15,
    ) -> list[SnapshotRebuildRequirement]:
        if not rows:
            return []
        oldest_by_tenant: dict[UUID, datetime] = {}
        for row in rows:
            cur = oldest_by_tenant.get(row.user_id)
            if cur is None or row.created_at < cur:
                oldest_by_tenant[row.user_id] = row.created_at

        now = datetime.now(UTC)
        adjusted: list[tuple[int, datetime, SnapshotRebuildRequirement]] = []
        for row in rows:
            priority = row.priority
            tenant_oldest = oldest_by_tenant.get(row.user_id, row.created_at)
            age_seconds = (now - tenant_oldest).total_seconds()
            if age_seconds > 3600 and priority > RebuildPriority.DRIFT_REPAIR:
                priority = max(RebuildPriority.SEMANTICS_INVALIDATION, priority - starvation_boost)
            adjusted.append((priority, row.created_at, row))

        adjusted.sort(key=lambda item: (item[0], item[1]))
        return [item[2] for item in adjusted]
