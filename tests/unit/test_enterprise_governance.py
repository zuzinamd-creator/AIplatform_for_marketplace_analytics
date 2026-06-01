"""Unit tests for enterprise autonomy governance."""

from __future__ import annotations

from app.core.config import settings
from app.runtime.enterprise.dto import OperationalDecisionKind
from app.runtime.enterprise.governance import AutonomyPermissionMatrix


def test_limited_level_blocks_defer(monkeypatch) -> None:
    monkeypatch.setattr(settings, "runtime_autonomy_safety_level", "limited")
    result = AutonomyPermissionMatrix.evaluate(
        OperationalDecisionKind.DEFER_REBUILD, dry_run=False
    )
    assert result.allowed is False


def test_standard_allows_stale_reset(monkeypatch) -> None:
    monkeypatch.setattr(settings, "runtime_autonomy_safety_level", "standard")
    result = AutonomyPermissionMatrix.evaluate(
        OperationalDecisionKind.RESET_STALE_REBUILD, dry_run=False
    )
    assert result.allowed is True
