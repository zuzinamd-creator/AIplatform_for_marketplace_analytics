"""Phase 9.18-B — dashboard summary slim payload / fan-out."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock, patch

import pytest

from app.core.user_roles import USER_ROLE_PLATFORM_ADMIN, USER_ROLE_SELLER
from app.models.report import Marketplace
from app.schemas.analytics import (
    AnalyticsFreshnessMeta,
    CostCoverageResponse,
    CostCoverageSkuRow,
)
from app.services.dashboard_service import (
    DashboardService,
    _slim_cost_coverage,
    _slim_todays_focus,
)


def _focus_raw(**overrides):
    base = SimpleNamespace(
        generated_at=datetime.now(UTC),
        headline="headline",
        requires_attention_today=["a"],
        can_wait=["b"],
        dangerous=["crit-1", "crit-2"],
        highest_upside=["u"],
        top_actions=[{"x": 1}],
        critical_alerts=[{"y": 2}],
        quick_wins=[{"z": 3}],
        priority_queue=[
            SimpleNamespace(
                recommendation_id="r1",
                title="t",
                summary="s" * 500,
                recommendation_score=1.0,
                priority_tier="today",
                priority_score=1.0,
                seller_usefulness={"huge": "x" * 1000},
            )
        ],
        advisory_notice="notice",
    )
    for k, v in overrides.items():
        setattr(base, k, v)
    return base


def test_slim_todays_focus_drops_priority_queue_and_unused_lists():
    slim = _slim_todays_focus(_focus_raw())
    assert slim.dangerous == ["crit-1", "crit-2"]
    assert slim.priority_queue == []
    assert slim.requires_attention_today == []
    assert slim.top_actions == []
    assert slim.headline == "headline"
    assert slim.advisory_notice == "notice"


def test_slim_cost_coverage_caps_missing_skus_and_clears_items():
    raw = CostCoverageResponse(
        marketplace=Marketplace.WILDBERRIES,
        period_start=date(2026, 7, 6),
        period_end=date(2026, 7, 12),
        total_skus=50,
        covered_skus=10,
        sku_cost_coverage_pct=Decimal("20"),
        cost_completeness_score=Decimal("20"),
        items=[
            CostCoverageSkuRow(
                sku="SKU-1",
                units_sold=1,
                revenue=Decimal("100"),
                cogs=Decimal("10"),
            )
        ],
        missing_skus=[f"SKU-{i}" for i in range(40)],
        freshness=AnalyticsFreshnessMeta(generated_at=datetime.now(UTC)),
        warnings=[],
    )
    slim = _slim_cost_coverage(raw)
    assert slim.items == []
    assert len(slim.missing_skus) == 20
    assert slim.covered_skus == 10
    assert slim.total_skus == 50


@pytest.mark.asyncio
async def test_summary_seller_uses_eight_fanout_branches():
    user = SimpleNamespace(id=uuid4(), role=USER_ROLE_SELLER)
    service = DashboardService(db=MagicMock(), user=user)  # type: ignore[arg-type]
    focus = _focus_raw()
    validated = MagicMock()
    fake_results = [focus, 1, 2, 3, 4, 5, 6, 7]
    captured: list = []

    async def capture_gather(*coros, **_k):
        captured.extend(coros)
        return fake_results

    with (
        patch("app.services.dashboard_service.asyncio.gather", side_effect=capture_gather),
        patch.object(DashboardService, "_run", side_effect=lambda fn: fn),
        patch("app.services.dashboard_service.RevenueKpiSummaryResponse.model_validate", return_value=validated),
        patch("app.services.dashboard_service.RevenueTrendResponse.model_validate", return_value=validated),
        patch("app.services.dashboard_service.FinancialKpiSummaryResponse.model_validate", return_value=validated),
        patch("app.services.dashboard_service.FinancialTrendsResponse.model_validate", return_value=validated),
        patch("app.services.dashboard_service.TopSkusResponse.model_validate", return_value=validated),
        patch("app.services.dashboard_service.AnalyticsCoverageResponse.model_validate", return_value=validated),
        patch("app.services.dashboard_service._slim_cost_coverage", return_value=validated),
        patch("app.services.dashboard_service.is_platform_admin", return_value=False),
        patch(
            "app.services.dashboard_service.DashboardSummaryResponse",
            side_effect=lambda **kw: SimpleNamespace(**kw),
        ),
    ):
        result = await service.summary(
            marketplace=Marketplace.WILDBERRIES,
            start=date(2026, 7, 6),
            end=date(2026, 7, 12),
        )

    assert len(captured) == 8
    assert result.recommendations.items == []
    assert result.recommendations.page.total == 0
    assert result.queue.items == []
    assert result.todays_focus.priority_queue == []
    assert result.todays_focus.dangerous == ["crit-1", "crit-2"]


@pytest.mark.asyncio
async def test_summary_admin_adds_ops_branches_and_rec_total():
    user = SimpleNamespace(id=uuid4(), role=USER_ROLE_PLATFORM_ADMIN)
    service = DashboardService(db=MagicMock(), user=user)  # type: ignore[arg-type]
    focus = _focus_raw()
    validated = MagicMock()
    runtime = MagicMock()
    ai_ops = SimpleNamespace(
        overall_score=1.0,
        degraded_intelligence_mode=True,
        runs_total=3,
        success_rate=1.0,
        pending_approvals=0,
        avg_confidence=None,
        recommendations=["keep"],
    )
    # 8 critical + queue + ai_ops + count_recs (runtime from shared cache, not a fan-out)
    fake_results = [
        focus,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        ([], 42, {"queued": 2}),
        ai_ops,
        7,
    ]
    captured: list = []

    async def capture_gather(*coros, **_k):
        captured.extend(coros)
        return fake_results

    from app.services.dashboard_query_cache import DashboardQueryCache

    cache = DashboardQueryCache()
    cache.runtime = runtime

    with (
        patch("app.services.dashboard_service.asyncio.gather", side_effect=capture_gather),
        patch.object(DashboardService, "_run", side_effect=lambda fn: fn),
        patch("app.services.dashboard_service.DashboardQueryCache", return_value=cache),
        patch("app.services.dashboard_service.RevenueKpiSummaryResponse.model_validate", return_value=validated),
        patch("app.services.dashboard_service.RevenueTrendResponse.model_validate", return_value=validated),
        patch("app.services.dashboard_service.FinancialKpiSummaryResponse.model_validate", return_value=validated),
        patch("app.services.dashboard_service.FinancialTrendsResponse.model_validate", return_value=validated),
        patch("app.services.dashboard_service.TopSkusResponse.model_validate", return_value=validated),
        patch("app.services.dashboard_service.AnalyticsCoverageResponse.model_validate", return_value=validated),
        patch("app.services.dashboard_service._slim_cost_coverage", return_value=validated),
        patch("app.services.dashboard_service.is_platform_admin", return_value=True),
        patch(
            "app.services.dashboard_service.DashboardSummaryResponse",
            side_effect=lambda **kw: SimpleNamespace(**kw),
        ),
    ):
        result = await service.summary(
            marketplace=Marketplace.WILDBERRIES,
            start=date(2026, 7, 6),
            end=date(2026, 7, 12),
        )

    assert len(captured) == 11
    assert result.recommendations.items == []
    assert result.recommendations.page.total == 7
    assert result.queue.items == []
    assert result.queue.status_counts == {"queued": 2}
    assert result.ai_ops.degraded_intelligence_mode is True
    assert result.todays_focus.priority_queue == []
    assert result.runtime is runtime
