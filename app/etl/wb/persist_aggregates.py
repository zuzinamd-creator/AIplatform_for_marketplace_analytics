"""WB financial persist — daily and SKU aggregate rebuild from ledger."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.analytics.aggregation import AggregationEngine
from app.domain.finance.types import LedgerEntryDraft, SkuCostSnapshot
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

    async def _rebuild_aggregates(self, *, result: WbFinancialProcessResult) -> None:
        affected_dates = {item.aggregate_date for item in result.daily_aggregates}
        for metric_date in affected_dates:
            await self._rebuild_daily_for_date(metric_date)
            await self._rebuild_sku_for_date(metric_date)
            await self._rebuild_sku_unit_economics_for_date(metric_date)

    async def _rebuild_daily_for_date(self, metric_date: date) -> None:
        entries = await self.db.execute(
            select(FinancialLedgerEntry).where(
                FinancialLedgerEntry.user_id == self.user_id,
                FinancialLedgerEntry.operation_date == metric_date,
            )
        )
        ledger = list(entries.scalars().all())
        costs = await self.load_cost_snapshots(self.db, self.user_id)
        drafts = [
            LedgerEntryDraft(
                operation_date=item.operation_date,
                sku=item.sku,
                nm_id=item.nm_id,
                operation_type=item.operation_type,
                amount=item.amount,
                currency=item.currency,
                source_row_id=item.source_row_id,
            )
            for item in ledger
        ]
        daily, _ = AggregationEngine.build(
            drafts,
            marketplace=Marketplace.WILDBERRIES,
            costs_by_sku=costs,
            default_date=metric_date,
        )
        if not daily:
            return
        row = daily[0]
        stmt = insert(DailyAggregate).values(
            user_id=self.user_id,
            aggregate_date=row.aggregate_date,
            marketplace=row.marketplace,
            revenue=row.revenue,
            net_profit=row.net_profit,
            margin=row.margin,
            roi=row.roi,
            return_rate=row.return_rate,
            buyout_rate=row.buyout_rate,
            average_check=row.average_check,
            units_sold=row.units_sold,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_daily_aggregate_day_marketplace",
            set_={
                "revenue": row.revenue,
                "net_profit": row.net_profit,
                "margin": row.margin,
                "roi": row.roi,
                "return_rate": row.return_rate,
                "buyout_rate": row.buyout_rate,
                "average_check": row.average_check,
                "units_sold": row.units_sold,
            },
        )
        await self.db.execute(stmt)

    async def _rebuild_sku_for_date(self, metric_date: date) -> None:
        entries = await self.db.execute(
            select(FinancialLedgerEntry).where(
                FinancialLedgerEntry.user_id == self.user_id,
                FinancialLedgerEntry.operation_date == metric_date,
                FinancialLedgerEntry.sku.is_not(None),
            )
        )
        ledger = list(entries.scalars().all())
        costs = await self.load_cost_snapshots(self.db, self.user_id)
        drafts = [
            LedgerEntryDraft(
                operation_date=item.operation_date,
                sku=item.sku,
                nm_id=item.nm_id,
                operation_type=item.operation_type,
                amount=item.amount,
                currency=item.currency,
                source_row_id=item.source_row_id,
            )
            for item in ledger
        ]
        _, sku_rows = AggregationEngine.build(
            drafts,
            marketplace=Marketplace.WILDBERRIES,
            costs_by_sku=costs,
            default_date=metric_date,
        )
        for row in sku_rows:
            if row.metric_date != metric_date or not row.sku:
                continue
            stmt = insert(SkuDailyMetric).values(
                user_id=self.user_id,
                sku=row.sku,
                metric_date=row.metric_date,
                marketplace=row.marketplace,
                revenue=row.revenue,
                net_profit=row.net_profit,
                margin=row.margin,
                roi=row.roi,
                return_rate=row.return_rate,
                buyout_rate=row.buyout_rate,
                average_check=row.average_check,
                units_sold=row.units_sold,
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_sku_daily_metric",
                set_={
                    "revenue": row.revenue,
                    "net_profit": row.net_profit,
                    "margin": row.margin,
                    "roi": row.roi,
                    "return_rate": row.return_rate,
                    "buyout_rate": row.buyout_rate,
                    "average_check": row.average_check,
                    "units_sold": row.units_sold,
                },
            )
            await self.db.execute(stmt)

    async def _rebuild_sku_unit_economics_for_date(self, metric_date: date) -> None:
        # Compute SKU-level economics breakdown from ledger + effective costs.
        entries = await self.db.execute(
            select(FinancialLedgerEntry).where(
                FinancialLedgerEntry.user_id == self.user_id,
                FinancialLedgerEntry.operation_date == metric_date,
                FinancialLedgerEntry.sku.is_not(None),
            )
        )
        ledger = list(entries.scalars().all())
        if not ledger:
            return

        costs = await self.load_cost_snapshots(self.db, self.user_id)

        by_sku: dict[str, list[FinancialLedgerEntry]] = {}
        for e in ledger:
            if not e.sku:
                continue
            by_sku.setdefault(str(e.sku), []).append(e)

        for sku, rows in by_sku.items():
            sums: dict[str, Decimal] = {}
            units_sold = 0
            for r in rows:
                op = r.operation_type.value
                sums[op] = sums.get(op, Decimal("0")) + Decimal(r.amount)
                if r.operation_type.value == "sale" and Decimal(r.amount) > 0:
                    units_sold += 1

            revenue = sums.get("sale", Decimal("0"))
            returns_amount = abs(sums.get("return", Decimal("0")))
            payout = sums.get("payout", Decimal("0"))
            commissions = abs(sums.get("commission", Decimal("0")))
            logistics = abs(sums.get("logistics", Decimal("0")))
            storage = abs(sums.get("storage_fee", Decimal("0")))
            ads = abs(sums.get("advertisement", Decimal("0")))
            penalties = abs(sums.get("penalty", Decimal("0")))
            acquiring = abs(sums.get("acquiring", Decimal("0")))
            deductions = abs(sums.get("deduction", Decimal("0")))
            compensation = sums.get("compensation", Decimal("0"))

            # COGS: units_sold × effective unit cost on that day.
            unit_cost = None
            history = costs.get(sku, [])
            if history:
                applicable = [item for item in history if item.effective_from <= metric_date]
                if applicable:
                    unit_cost = max(applicable, key=lambda item: item.effective_from).total_unit_cost
            cogs = (unit_cost * Decimal(units_sold)) if unit_cost is not None else Decimal("0")

            # Gross profit / contribution margin:
            # profit = (revenue - returns) + compensation - (fees...) - cogs
            gross_profit = (revenue - returns_amount) + compensation
            contribution_margin = gross_profit - commissions - logistics - storage - ads - penalties - acquiring - deductions - cogs

            margin_pct = (contribution_margin / revenue * Decimal("100")) if revenue > 0 else None
            return_rate = (returns_amount / revenue * Decimal("100")) if revenue > 0 else None
            ad_cost_ratio = (ads / revenue * Decimal("100")) if revenue > 0 else None
            logistics_burden = (logistics / revenue * Decimal("100")) if revenue > 0 else None

            stmt = insert(SkuUnitEconomicsDaily).values(
                user_id=self.user_id,
                sku=sku,
                metric_date=metric_date,
                marketplace=Marketplace.WILDBERRIES,
                units_sold=units_sold,
                revenue=revenue,
                returns_amount=returns_amount,
                payout=payout,
                commissions=commissions,
                logistics=logistics,
                storage=storage,
                ads=ads,
                penalties=penalties,
                acquiring=acquiring,
                deductions=deductions,
                compensation=compensation,
                acceptance_fees=Decimal("0"),
                loyalty_compensation=Decimal("0"),
                cogs=cogs,
                gross_profit=gross_profit,
                contribution_margin=contribution_margin,
                margin_pct=margin_pct,
                return_rate=return_rate,
                ad_cost_ratio=ad_cost_ratio,
                logistics_burden=logistics_burden,
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_sku_unit_econ_daily",
                set_={
                    "units_sold": units_sold,
                    "revenue": revenue,
                    "returns_amount": returns_amount,
                    "payout": payout,
                    "commissions": commissions,
                    "logistics": logistics,
                    "storage": storage,
                    "ads": ads,
                    "penalties": penalties,
                    "acquiring": acquiring,
                    "deductions": deductions,
                    "compensation": compensation,
                    "cogs": cogs,
                    "gross_profit": gross_profit,
                    "contribution_margin": contribution_margin,
                    "margin_pct": margin_pct,
                    "return_rate": return_rate,
                    "ad_cost_ratio": ad_cost_ratio,
                    "logistics_burden": logistics_burden,
                },
            )
            await self.db.execute(stmt)
