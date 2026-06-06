"""WB financial persist — daily and SKU aggregate rebuild from ledger."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.analytics.aggregation import AggregationEngine, DailyAggregateDraft, SkuDailyMetricDraft
from app.domain.economics.sku_unit_economics_builder import SkuUnitEconomicsBuilder, SkuUnitEconomicsDraft
from app.domain.finance.types import LedgerEntryDraft, SkuCostSnapshot
from app.etl.db_batch import INSERT_BATCH_SIZE, iter_batches
from app.etl.wb.types import WbFinancialProcessResult
from app.models.cost_history import CostHistory
from app.models.economics.sku_unit_economics import SkuUnitEconomicsDaily
from app.models.finance import DailyAggregate, FinancialLedgerEntry, SkuDailyMetric
from app.models.report import Marketplace


class WbPersistAggregatesMixin:
    """Aggregate rebuild helpers; mixed into WbFinancialPersistService."""

    db: AsyncSession
    user_id: UUID

    @staticmethod
    async def load_cost_snapshots(
        db: AsyncSession,
        user_id: UUID,
    ) -> dict[str, list[SkuCostSnapshot]]:
        result = await db.execute(select(CostHistory).where(CostHistory.user_id == user_id))
        costs: dict[str, list[SkuCostSnapshot]] = {}
        for row in result.scalars().all():
            costs.setdefault(row.internal_sku, []).append(
                SkuCostSnapshot(
                    sku=row.internal_sku,
                    effective_from=row.effective_from,
                    product_cost=row.product_cost,
                    packaging_cost=row.packaging_cost,
                    inbound_logistics_cost=row.inbound_logistics_cost,
                    additional_cost=row.additional_cost,
                    currency=row.currency,
                )
            )
        return costs

    async def _resolve_affected_dates(
        self,
        *,
        result: WbFinancialProcessResult,
        report_id: UUID,
    ) -> set[date]:
        affected_dates = {item.aggregate_date for item in result.daily_aggregates}
        if affected_dates:
            return affected_dates
        rows = await self.db.execute(
            select(FinancialLedgerEntry.operation_date)
            .where(
                FinancialLedgerEntry.user_id == self.user_id,
                FinancialLedgerEntry.report_id == report_id,
            )
            .distinct()
        )
        return {value for (value,) in rows.all() if value is not None}

    async def _rebuild_aggregates(
        self,
        *,
        result: WbFinancialProcessResult,
        report_id: UUID,
        costs_by_sku: dict[str, list[SkuCostSnapshot]] | None = None,
    ) -> None:
        """
        Rebuild day-level projections from full ledger history on affected dates.

        Idempotent on retry: SKU-level rows for the period are removed first, then
        recomputed from ledger (prevents stale SKU rows after re-import). Day-level
        totals use ON CONFLICT DO UPDATE (full row replace per date/marketplace).
        """
        affected_dates = await self._resolve_affected_dates(result=result, report_id=report_id)
        if not affected_dates:
            return

        costs = (
            costs_by_sku
            if costs_by_sku is not None
            else await self.load_cost_snapshots(self.db, self.user_id)
        )
        drafts = await self._load_ledger_drafts_for_dates(affected_dates)
        if not drafts:
            return

        daily, sku_rows = AggregationEngine.build(
            drafts,
            marketplace=Marketplace.WILDBERRIES,
            costs_by_sku=costs,
            default_date=result.default_date,
        )
        unit_econ_rows = SkuUnitEconomicsBuilder.build(
            drafts,
            marketplace=Marketplace.WILDBERRIES,
            costs_by_sku=costs,
            affected_dates=affected_dates,
        )

        marketplace_value = Marketplace.WILDBERRIES.value
        await self._purge_sku_aggregates_for_dates(affected_dates, marketplace=marketplace_value)
        await self._batch_upsert_daily_aggregates(daily, affected_dates)
        await self._batch_upsert_sku_daily_metrics(sku_rows, affected_dates)
        await self._batch_upsert_sku_unit_economics(unit_econ_rows)

    async def _purge_sku_aggregates_for_dates(
        self,
        affected_dates: set[date],
        *,
        marketplace: str,
    ) -> None:
        """Drop SKU projections for affected dates so retry cannot leave orphan rows."""
        if not affected_dates:
            return
        await self.db.execute(
            delete(SkuDailyMetric).where(
                SkuDailyMetric.user_id == self.user_id,
                SkuDailyMetric.metric_date.in_(affected_dates),
                SkuDailyMetric.marketplace == marketplace,
            )
        )
        await self.db.execute(
            delete(SkuUnitEconomicsDaily).where(
                SkuUnitEconomicsDaily.user_id == self.user_id,
                SkuUnitEconomicsDaily.metric_date.in_(affected_dates),
                SkuUnitEconomicsDaily.marketplace == marketplace,
            )
        )

    async def _load_ledger_drafts_for_dates(self, dates: set[date]) -> list[LedgerEntryDraft]:
        result = await self.db.execute(
            select(FinancialLedgerEntry).where(
                FinancialLedgerEntry.user_id == self.user_id,
                FinancialLedgerEntry.operation_date.in_(dates),
            )
        )
        return [
            LedgerEntryDraft(
                operation_date=item.operation_date,
                sku=item.sku,
                nm_id=item.nm_id,
                operation_type=item.operation_type,
                amount=item.amount,
                currency=item.currency,
                source_row_id=item.source_row_id,
            )
            for item in result.scalars().all()
        ]

    async def _batch_upsert_daily_aggregates(
        self,
        daily: list[DailyAggregateDraft],
        affected_dates: set[date],
    ) -> None:
        values = [
            {
                "user_id": self.user_id,
                "aggregate_date": row.aggregate_date,
                "marketplace": row.marketplace,
                "revenue": row.revenue,
                "net_profit": row.net_profit,
                "margin": row.margin,
                "roi": row.roi,
                "return_rate": row.return_rate,
                "buyout_rate": row.buyout_rate,
                "average_check": row.average_check,
                "units_sold": row.units_sold,
            }
            for row in daily
            if row.aggregate_date in affected_dates
        ]
        if not values:
            return
        upsert = insert(DailyAggregate)
        upsert = upsert.on_conflict_do_update(
            constraint="uq_daily_aggregate_day_marketplace",
            set_={
                "revenue": upsert.excluded.revenue,
                "net_profit": upsert.excluded.net_profit,
                "margin": upsert.excluded.margin,
                "roi": upsert.excluded.roi,
                "return_rate": upsert.excluded.return_rate,
                "buyout_rate": upsert.excluded.buyout_rate,
                "average_check": upsert.excluded.average_check,
                "units_sold": upsert.excluded.units_sold,
            },
        )
        for batch in iter_batches(values, batch_size=INSERT_BATCH_SIZE):
            await self.db.execute(upsert, batch)

    async def _batch_upsert_sku_daily_metrics(
        self,
        sku_rows: list[SkuDailyMetricDraft],
        affected_dates: set[date],
    ) -> None:
        values = [
            {
                "user_id": self.user_id,
                "sku": row.sku,
                "metric_date": row.metric_date,
                "marketplace": row.marketplace,
                "revenue": row.revenue,
                "net_profit": row.net_profit,
                "margin": row.margin,
                "roi": row.roi,
                "return_rate": row.return_rate,
                "buyout_rate": row.buyout_rate,
                "average_check": row.average_check,
                "units_sold": row.units_sold,
            }
            for row in sku_rows
            if row.metric_date in affected_dates and row.sku
        ]
        if not values:
            return
        upsert = insert(SkuDailyMetric)
        upsert = upsert.on_conflict_do_update(
            constraint="uq_sku_daily_metric",
            set_={
                "revenue": upsert.excluded.revenue,
                "net_profit": upsert.excluded.net_profit,
                "margin": upsert.excluded.margin,
                "roi": upsert.excluded.roi,
                "return_rate": upsert.excluded.return_rate,
                "buyout_rate": upsert.excluded.buyout_rate,
                "average_check": upsert.excluded.average_check,
                "units_sold": upsert.excluded.units_sold,
            },
        )
        for batch in iter_batches(values, batch_size=INSERT_BATCH_SIZE):
            await self.db.execute(upsert, batch)

    async def _batch_upsert_sku_unit_economics(self, rows: list[SkuUnitEconomicsDraft]) -> None:
        if not rows:
            return
        values = [
            {
                "user_id": self.user_id,
                "sku": row.sku,
                "metric_date": row.metric_date,
                "marketplace": row.marketplace,
                "units_sold": row.units_sold,
                "revenue": row.revenue,
                "returns_amount": row.returns_amount,
                "payout": row.payout,
                "commissions": row.commissions,
                "logistics": row.logistics,
                "storage": row.storage,
                "ads": row.ads,
                "penalties": row.penalties,
                "acquiring": row.acquiring,
                "deductions": row.deductions,
                "compensation": row.compensation,
                "acceptance_fees": Decimal("0"),
                "loyalty_compensation": Decimal("0"),
                "cogs": row.cogs,
                "gross_profit": row.gross_profit,
                "contribution_margin": row.contribution_margin,
                "margin_pct": row.margin_pct,
                "return_rate": row.return_rate,
                "ad_cost_ratio": row.ad_cost_ratio,
                "logistics_burden": row.logistics_burden,
            }
            for row in rows
        ]
        upsert = insert(SkuUnitEconomicsDaily)
        upsert = upsert.on_conflict_do_update(
            constraint="uq_sku_unit_econ_daily",
            set_={
                "units_sold": upsert.excluded.units_sold,
                "revenue": upsert.excluded.revenue,
                "returns_amount": upsert.excluded.returns_amount,
                "payout": upsert.excluded.payout,
                "commissions": upsert.excluded.commissions,
                "logistics": upsert.excluded.logistics,
                "storage": upsert.excluded.storage,
                "ads": upsert.excluded.ads,
                "penalties": upsert.excluded.penalties,
                "acquiring": upsert.excluded.acquiring,
                "deductions": upsert.excluded.deductions,
                "compensation": upsert.excluded.compensation,
                "cogs": upsert.excluded.cogs,
                "gross_profit": upsert.excluded.gross_profit,
                "contribution_margin": upsert.excluded.contribution_margin,
                "margin_pct": upsert.excluded.margin_pct,
                "return_rate": upsert.excluded.return_rate,
                "ad_cost_ratio": upsert.excluded.ad_cost_ratio,
                "logistics_burden": upsert.excluded.logistics_burden,
            },
        )
        for batch in iter_batches(values, batch_size=INSERT_BATCH_SIZE):
            await self.db.execute(upsert, batch)

    async def rebuild_projections_for_dates(
        self,
        affected_dates: set[date],
        *,
        default_date: date | None = None,
    ) -> None:
        """Rebuild or clear day/SKU projections after ledger mutations (e.g. report delete)."""
        if not affected_dates:
            return

        costs = await self.load_cost_snapshots(self.db, self.user_id)
        await self._purge_sku_aggregates_for_dates(
            affected_dates,
            marketplace=Marketplace.WILDBERRIES.value,
        )
        drafts = await self._load_ledger_drafts_for_dates(affected_dates)
        if not drafts:
            await self.db.execute(
                delete(DailyAggregate).where(
                    DailyAggregate.user_id == self.user_id,
                    DailyAggregate.aggregate_date.in_(affected_dates),
                    DailyAggregate.marketplace == Marketplace.WILDBERRIES,
                )
            )
            return

        fallback = default_date or min(affected_dates)
        daily, sku_rows = AggregationEngine.build(
            drafts,
            marketplace=Marketplace.WILDBERRIES,
            costs_by_sku=costs,
            default_date=fallback,
        )
        unit_econ_rows = SkuUnitEconomicsBuilder.build(
            drafts,
            marketplace=Marketplace.WILDBERRIES,
            costs_by_sku=costs,
            affected_dates=affected_dates,
        )
        dates_with_totals = {row.aggregate_date for row in daily}
        orphan_dates = affected_dates - dates_with_totals
        if orphan_dates:
            await self.db.execute(
                delete(DailyAggregate).where(
                    DailyAggregate.user_id == self.user_id,
                    DailyAggregate.aggregate_date.in_(orphan_dates),
                    DailyAggregate.marketplace == Marketplace.WILDBERRIES,
                )
            )
        await self._batch_upsert_daily_aggregates(daily, affected_dates)
        await self._batch_upsert_sku_daily_metrics(sku_rows, affected_dates)
        await self._batch_upsert_sku_unit_economics(unit_econ_rows)
