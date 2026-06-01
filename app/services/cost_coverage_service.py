"""Deterministic cost coverage intelligence (tenant-scoped, read-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cost_history import CostHistory
from app.models.economics.sku_unit_economics import SkuUnitEconomicsDaily
from app.models.report import Marketplace
from app.schemas.analytics import (
    AnalyticsFreshnessMeta,
    CostCoverageResponse,
    CostCoverageSkuRow,
    IntegrityWarning,
)
from app.services.base import TenantScopedService
from app.services.ops_service import OpsService


@dataclass(frozen=True)
class CoveragePeriod:
    start: date
    end: date


class CostCoverageService(TenantScopedService):
    def __init__(self, db: AsyncSession, user_id):
        super().__init__(db, user_id=user_id)

    async def _freshness(self) -> AnalyticsFreshnessMeta:
        runtime = await OpsService(self.db, type("U", (), {"id": self.user_id})()).runtime_summary()  # lightweight shim
        # data_as_of: max economics date
        stmt = select(func.max(SkuUnitEconomicsDaily.metric_date))
        res = await self.execute_with_rls(stmt)
        data_as_of = res.scalar_one_or_none()
        stale = (runtime.rebuild.running > 0) or (runtime.rebuild.pending_dispatch > 0)
        from datetime import UTC, datetime

        return AnalyticsFreshnessMeta(
            semantics_version="1.0",
            data_as_of=data_as_of,
            rebuild_running=runtime.rebuild.running,
            rebuild_pending=runtime.rebuild.pending_dispatch,
            queue_processing=runtime.queue.processing_count,
            queue_pending=runtime.queue.pending_count,
            dead_letters=runtime.queue.dead_letter_count,
            stale_data_warning=stale,
            degraded_mode=False,
            generated_at=datetime.now(UTC),
        )

    async def analyze(
        self,
        *,
        marketplace: Marketplace,
        period: CoveragePeriod,
        limit: int = 50,
        sku_query: str | None = None,
    ) -> CostCoverageResponse:
        freshness = await self._freshness()

        filters = [
            SkuUnitEconomicsDaily.marketplace == marketplace,
            SkuUnitEconomicsDaily.metric_date >= period.start,
            SkuUnitEconomicsDaily.metric_date <= period.end,
        ]
        if sku_query:
            filters.append(SkuUnitEconomicsDaily.sku.ilike(f"%{sku_query}%"))

        totals_stmt = select(
            func.count(func.distinct(SkuUnitEconomicsDaily.sku)),
            func.coalesce(func.sum(SkuUnitEconomicsDaily.units_sold), 0),
            func.coalesce(func.sum(SkuUnitEconomicsDaily.revenue), 0),
            func.coalesce(func.sum(SkuUnitEconomicsDaily.cogs), 0),
        ).where(*filters)
        totals_res = await self.execute_with_rls(totals_stmt)
        total_skus, units_sold, revenue_sum, cogs_sum = totals_res.one()

        covered_stmt = select(func.count(func.distinct(SkuUnitEconomicsDaily.sku))).where(*filters).where(
            SkuUnitEconomicsDaily.cogs > 0
        )
        covered_res = await self.execute_with_rls(covered_stmt)
        covered_skus = int(covered_res.scalar_one() or 0)

        total_skus_i = int(total_skus or 0)
        sku_cov = (
            (Decimal(covered_skus) / Decimal(total_skus_i) * Decimal("100"))
            if total_skus_i > 0
            else None
        )

        warnings: list[IntegrityWarning] = []
        if total_skus_i > 0 and covered_skus == 0 and Decimal(revenue_sum) > 0:
            warnings.append(
                IntegrityWarning(
                    code="missing_cogs",
                    severity="warning",
                    message="Себестоимость отсутствует: прибыль и маржа будут неполными до загрузки затрат.",
                )
            )

        # Duplicate imports heuristic: same (sku, effective_from, cost) repeated.
        dup_stmt = (
            select(func.count())
            .select_from(CostHistory)
            .group_by(CostHistory.internal_sku, CostHistory.effective_from, CostHistory.cost)
            .having(func.count() > 1)
        )
        dup_res = await self.execute_with_rls(dup_stmt)
        dup_groups = len(dup_res.all())
        if dup_groups > 0:
            warnings.append(
                IntegrityWarning(
                    code="duplicate_cost_imports",
                    severity="warning",
                    message="Обнаружены дубли себестоимости (одинаковые SKU/дата/стоимость). Это может искажать доверие к данным.",
                    context={"duplicate_groups": str(dup_groups)},
                )
            )

        # Per-SKU rows (top by revenue to help sellers prioritize).
        stmt = (
            select(
                SkuUnitEconomicsDaily.sku,
                func.coalesce(func.sum(SkuUnitEconomicsDaily.units_sold), 0).label("units_sold"),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.revenue), 0).label("revenue"),
                func.coalesce(func.sum(SkuUnitEconomicsDaily.cogs), 0).label("cogs"),
            )
            .where(*filters)
            .group_by(SkuUnitEconomicsDaily.sku)
            .order_by(func.sum(SkuUnitEconomicsDaily.revenue).desc())
            .limit(limit)
        )
        res = await self.execute_with_rls(stmt)

        items: list[CostCoverageSkuRow] = []
        max_age_days = 120
        cutoff = period.end - timedelta(days=max_age_days)
        for sku, u, rev, cogs in res.all():
            sku_warnings: list[IntegrityWarning] = []
            rev_d = Decimal(rev)
            cogs_d = Decimal(cogs)
            cov_pct = (Decimal("100") if (Decimal(u) > 0 and cogs_d > 0) else Decimal("0")) if int(u or 0) > 0 else None

            last_cost_stmt = (
                select(func.max(CostHistory.effective_from))
                .where(CostHistory.internal_sku == str(sku))
            )
            last_cost_res = await self.execute_with_rls(last_cost_stmt)
            last_cost = last_cost_res.scalar_one_or_none()

            if int(u or 0) > 0 and cogs_d == 0:
                sku_warnings.append(
                    IntegrityWarning(
                        code="missing_sku_cost",
                        severity="warning",
                        message="Нет себестоимости для SKU в периоде продаж.",
                    )
                )
            if last_cost and last_cost < cutoff:
                sku_warnings.append(
                    IntegrityWarning(
                        code="outdated_cost",
                        severity="info",
                        message="Себестоимость устарела (последняя дата слишком давно).",
                        context={"last_cost_effective_from": last_cost.isoformat()},
                    )
                )
            if last_cost is None:
                sku_warnings.append(
                    IntegrityWarning(
                        code="missing_supplier_price",
                        severity="info",
                        message="Не найдено ни одной записи себестоимости/цены поставщика для SKU.",
                    )
                )

            items.append(
                CostCoverageSkuRow(
                    sku=str(sku),
                    units_sold=int(u or 0),
                    revenue=rev_d,
                    cogs=cogs_d,
                    cost_coverage_pct=cov_pct,
                    last_cost_effective_from=last_cost,
                    warnings=sku_warnings,
                )
            )

        # Simple score: start from SKU coverage, penalize duplicates.
        score = sku_cov
        if score is not None and dup_groups > 0:
            score = max(Decimal("0"), score - Decimal("10"))

        return CostCoverageResponse(
            marketplace=marketplace,
            period_start=period.start,
            period_end=period.end,
            total_skus=total_skus_i,
            covered_skus=covered_skus,
            sku_cost_coverage_pct=sku_cov,
            cost_completeness_score=score,
            items=items,
            freshness=freshness,
            warnings=warnings,
        )

