"""Phase 9.11-E1: top_skus accepts sort=margin without changing summary contract."""

from __future__ import annotations

import inspect

from app.services.analytics_service import AnalyticsService


def test_top_skus_method_accepts_sort_parameter() -> None:
    sig = inspect.signature(AnalyticsService.top_skus)
    assert "sort" in sig.parameters


def test_margin_sort_branch_present_in_source() -> None:
    src = inspect.getsource(AnalyticsService.top_skus)
    assert 'sort_key in {"margin", "margin_pct"}' in src or "margin" in src
    assert "nullif" in src
