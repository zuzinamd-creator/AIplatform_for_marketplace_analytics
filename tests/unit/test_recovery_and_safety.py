"""Unit tests for recovery primitives and safety guard thresholds."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from app.models.semantics.governance import RebuildOrchestrationStatus, SnapshotRebuildRequirement
from app.operations.rebuild_orchestration import compute_next_eligible_at, is_eligible_for_dispatch
from app.operations.safety_guards import warn_rebuild_duration_high, warn_wal_growth_high


def test_warn_rebuild_duration_triggers_above_threshold() -> None:
    with patch("app.operations.safety_guards.settings") as mock_settings:
        mock_settings.ops_rebuild_duration_warn_ms = 1000
        result = warn_rebuild_duration_high(duration_ms=1500.0, user_id="u1", rebuild_mode="full")
    assert result.triggered is True
    assert result.value == 1500.0


def test_warn_wal_growth_below_threshold() -> None:
    with patch("app.operations.safety_guards.settings") as mock_settings:
        mock_settings.ops_wal_bytes_delta_warn = 1_000_000
        result = warn_wal_growth_high(wal_bytes_delta=500, user_id="u1")
    assert result.triggered is False


def test_is_eligible_respects_next_eligible_at() -> None:
    row = MagicMock(spec=SnapshotRebuildRequirement)
    row.requires_rebuild = True
    row.orchestration_status = RebuildOrchestrationStatus.DEFERRED
    row.attempt_count = 1
    row.max_attempts = 3
    row.next_eligible_at = datetime.now(UTC) + timedelta(hours=1)
    assert is_eligible_for_dispatch(row) is False

    row.next_eligible_at = datetime.now(UTC) - timedelta(seconds=1)
    assert is_eligible_for_dispatch(row) is True


def test_compute_backoff_capped() -> None:
    t = compute_next_eligible_at(20, base_delay_seconds=30)
    assert t <= datetime.now(UTC) + timedelta(seconds=3601)
