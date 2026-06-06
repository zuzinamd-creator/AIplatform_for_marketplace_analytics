"""Deterministic cost coverage intelligence (tenant-scoped, read-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.finance.cost_lookup import resolve_cost_snapshots, unit_cost_on_date
from app.etl.wb.persist_aggregates import WbPersistAggregatesMixin
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
        total_skus_i = int(total_skus or 0)

        gaps = await self.sales_coverage_gaps(
            marketplace=marketplace,
            period=period,
            limit=200,
        )
        covered_skus = int(gaps["covered_skus"])
        missing_skus: list[str] = list(gaps["missing_skus"])
        if gaps["total_selling_skus"]:
            total_skus_i = int(gaps["total_selling_skus"])
        sku_cov = gaps["sku_cost_coverage_pct"]

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
            cov_pct = (
                Decimal("100")
                if int(u or 0) > 0 and str(sku) not in missing_skus
                else (Decimal("0") if int(u or 0) > 0 else None)
            )

            last_cost_stmt = (
                select(func.max(CostHistory.effective_from))
                .where(CostHistory.internal_sku == str(sku))
            )
            last_cost_res = await self.execute_with_rls(last_cost_stmt)
            last_cost = last_cost_res.scalar_one_or_none()

            if int(u or 0) > 0 and cogs_d == 0 and str(sku) in missing_skus:
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
            missing_skus=missing_skus,
            freshness=freshness,
            warnings=warnings,
        )

    async def sales_coverage_gaps(
        self,
        *,
        marketplace: Marketplace,
        period: CoveragePeriod | None = None,
        limit: int = 50,
    ) -> dict:
        """Selling SKUs without cost for the sales period (for costs page / dashboard warnings)."""
        if period is None:
            bounds = await self.execute_with_rls(
                select(
                    func.min(SkuUnitEconomicsDaily.metric_date),
                    func.max(SkuUnitEconomicsDaily.metric_date),
                ).where(
                    SkuUnitEconomicsDaily.marketplace == marketplace,
                    SkuUnitEconomicsDaily.units_sold > 0,
                )
            )
            period_start, period_end = bounds.one()
            if period_start is None or period_end is None:
                return {
                    "marketplace": marketplace,
                    "period_start": None,
                    "period_end": None,
                    "total_selling_skus": 0,
                    "covered_skus": 0,
                    "sku_cost_coverage_pct": None,
                    "missing_skus": [],
                }
            period = CoveragePeriod(start=period_start, end=period_end)

        selling_stmt = (
            select(SkuUnitEconomicsDaily.sku)
            .where(
                SkuUnitEconomicsDaily.marketplace == marketplace,
                SkuUnitEconomicsDaily.metric_date >= period.start,
                SkuUnitEconomicsDaily.metric_date <= period.end,
                SkuUnitEconomicsDaily.units_sold > 0,
            )
            .group_by(SkuUnitEconomicsDaily.sku)
            .order_by(SkuUnitEconomicsDaily.sku.asc())
        )
        selling_res = await self.execute_with_rls(selling_stmt)
        selling_skus = [str(row[0]) for row in selling_res.all() if row[0]]
        if not selling_skus:
            return {
                "marketplace": marketplace,
                "period_start": period.start,
                "period_end": period.end,
                "total_selling_skus": 0,
                "covered_skus": 0,
                "sku_cost_coverage_pct": None,
                "missing_skus": [],
            }

        async with self._rls_transaction():
            cost_lookup = await WbPersistAggregatesMixin.load_cost_snapshots(self.db, self.user_id)

        missing: list[str] = []
        covered = 0
        for sku in selling_skus:
            history = resolve_cost_snapshots(cost_lookup, sku)
            if unit_cost_on_date(history, period.end) is not None:
                covered += 1
            else:
                missing.append(sku)

        total = len(selling_skus)
        pct = (Decimal(covered) / Decimal(total) * Decimal("100")).quantize(Decimal("0.01")) if total else None
        return {
            "marketplace": marketplace,
            "period_start": period.start,
            "period_end": period.end,
            "total_selling_skus": total,
            "covered_skus": covered,
            "sku_cost_coverage_pct": pct,
            "missing_skus": missing[:limit],
        }

