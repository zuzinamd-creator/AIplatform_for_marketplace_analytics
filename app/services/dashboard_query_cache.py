"""Request-scoped reuse for dashboard summary fan-out (Phase 9.18-D P1).

Caches expensive shared computations across parallel dashboard branches without
changing KPI / integrity formulas — only avoids duplicate work.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.domain.analytics.seller_kpis import SellerKpis
    from app.models.report import Marketplace
    from app.schemas.analytics import AnalyticsFreshnessMeta, AnalyticsIntegrityMeta
    from app.schemas.ops_runtime import RuntimeSummaryResponse
    from app.services.analytics_service import AnalyticsService, Period


def _period_key(marketplace: Marketplace, period: Period) -> tuple[str, str, str]:
    return (
        str(marketplace.value if hasattr(marketplace, "value") else marketplace),
        str(period.start),
        str(period.end),
    )


@dataclass
class DashboardQueryCache:
    """Async-safe memo for one GET /dashboard/summary request."""

    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    runtime: RuntimeSummaryResponse | None = None
    freshness: AnalyticsFreshnessMeta | None = None
    _seller_kpis: dict[tuple[str, str, str], Any] = field(default_factory=dict)
    _integrity: dict[tuple[str, str, str, str], Any] = field(default_factory=dict)
    _runtime_task: asyncio.Task | None = field(default=None, repr=False)
    _freshness_task: asyncio.Task | None = field(default=None, repr=False)
    _kpi_tasks: dict[tuple[str, str, str], asyncio.Task] = field(default_factory=dict, repr=False)
    _integrity_tasks: dict[tuple[str, str, str, str], asyncio.Task] = field(
        default_factory=dict, repr=False
    )

    async def get_runtime(self, factory) -> RuntimeSummaryResponse:
        async with self._lock:
            if self.runtime is not None:
                return self.runtime
            if self._runtime_task is None:
                self._runtime_task = asyncio.create_task(factory())
            task = self._runtime_task
        result = await task
        async with self._lock:
            self.runtime = result
            return self.runtime

    async def get_freshness(
        self,
        analytics: AnalyticsService,
        *,
        semantics_version: str = "1.0",
    ) -> AnalyticsFreshnessMeta:
        async with self._lock:
            if self.freshness is not None:
                return self.freshness
            if self._freshness_task is None:
                self._freshness_task = asyncio.create_task(
                    self._build_freshness(analytics, semantics_version=semantics_version)
                )
            task = self._freshness_task
        return await task

    async def _build_freshness(
        self,
        analytics: AnalyticsService,
        *,
        semantics_version: str,
    ) -> AnalyticsFreshnessMeta:
        from datetime import UTC, datetime

        from app.schemas.analytics import AnalyticsFreshnessMeta
        from app.services.ops_service import OpsService

        runtime = await self.get_runtime(
            lambda: OpsService(analytics.db, analytics.user).runtime_summary()
        )
        data_as_of = await analytics._max_aggregate_date()
        rebuild = runtime.rebuild
        queue = runtime.queue
        stale = (rebuild.running > 0) or (rebuild.pending_dispatch > 0)
        freshness = AnalyticsFreshnessMeta(
            semantics_version=semantics_version,
            data_as_of=data_as_of,
            rebuild_running=rebuild.running,
            rebuild_pending=rebuild.pending_dispatch,
            queue_processing=queue.processing_count,
            queue_pending=queue.pending_count,
            dead_letters=queue.dead_letter_count,
            stale_data_warning=stale,
            degraded_mode=runtime.health.overall_severity.value.lower() in ("warning", "critical")
            if hasattr(runtime.health.overall_severity, "value")
            else False,
            generated_at=datetime.now(UTC),
        )
        async with self._lock:
            self.freshness = freshness
        return freshness

    async def get_seller_kpis(
        self,
        analytics: AnalyticsService,
        *,
        marketplace: Marketplace,
        period: Period,
    ) -> SellerKpis:
        key = _period_key(marketplace, period)
        async with self._lock:
            cached = self._seller_kpis.get(key)
            if cached is not None:
                return cached
            if key not in self._kpi_tasks:
                self._kpi_tasks[key] = asyncio.create_task(
                    analytics._wb_seller_kpis_uncached(marketplace=marketplace, period=period)
                )
            task = self._kpi_tasks[key]
        value = await task
        async with self._lock:
            self._seller_kpis[key] = value
            return value

    async def get_integrity(
        self,
        analytics: AnalyticsService,
        *,
        marketplace: Marketplace,
        period: Period,
        semantics_version: str = "1.0",
    ) -> AnalyticsIntegrityMeta | None:
        key = (*_period_key(marketplace, period), semantics_version)
        async with self._lock:
            if key in self._integrity:
                return self._integrity[key]
            if key not in self._integrity_tasks:
                self._integrity_tasks[key] = asyncio.create_task(
                    analytics._integrity_uncached(
                        marketplace=marketplace,
                        period=period,
                        semantics_version=semantics_version,
                    )
                )
            task = self._integrity_tasks[key]
        value = await task
        async with self._lock:
            self._integrity[key] = value
            return value
