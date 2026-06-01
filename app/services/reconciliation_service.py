"""Deterministic marketplace reconciliation (tenant-scoped, read-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.economics.reconciliation_math import expected_payout
from app.models.economics.sku_unit_economics import SkuUnitEconomicsDaily
from app.models.finance.enums import LedgerOperationType
from app.models.finance.ledger import FinancialLedgerEntry
from app.models.report import Marketplace
from app.schemas.analytics import (
    AnalyticsFreshnessMeta,
    IntegrityWarning,
    ReconciliationBreakdown,
    ReconciliationResponse,
)
from app.services.base import TenantScopedService
from app.services.ops_service import OpsService


@dataclass(frozen=True)
class ReconciliationPeriod:
    start: date
    end: date


class ReconciliationService(TenantScopedService):
    def __init__(self, db: AsyncSession, user_id):
        super().__init__(db, user_id=user_id)

    async def _freshness(self) -> AnalyticsFreshnessMeta:
        runtime = await OpsService(self.db, type("U", (), {"id": self.user_id})()).runtime_summary()
        stmt = select(func.max(FinancialLedgerEntry.operation_date))
        res = await self.execute_with_rls(stmt)
        data_as_of = res.scalar_one_or_none()
        stale = (runtime.rebuild.running > 0) or (runtime.rebuild.pending_dispatch > 0)
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

    async def reconcile(self, *, marketplace: Marketplace, period: ReconciliationPeriod) -> ReconciliationResponse:
        freshness = await self._freshness()

        stmt = (
            select(FinancialLedgerEntry.operation_type, func.coalesce(func.sum(FinancialLedgerEntry.amount), 0))
            .where(FinancialLedgerEntry.operation_date >= period.start)
            .where(FinancialLedgerEntry.operation_date <= period.end)
            .group_by(FinancialLedgerEntry.operation_type)
        )
        res = await self.execute_with_rls(stmt)
        sums = {op: Decimal(total) for op, total in res.all()}

        revenue = sums.get(LedgerOperationType.SALE, Decimal("0"))
        returns_amount = abs(sums.get(LedgerOperationType.RETURN, Decimal("0")))
        commissions = abs(sums.get(LedgerOperationType.COMMISSION, Decimal("0")))
        logistics = abs(sums.get(LedgerOperationType.LOGISTICS, Decimal("0")))
        storage = abs(sums.get(LedgerOperationType.STORAGE_FEE, Decimal("0")))
        ads = abs(sums.get(LedgerOperationType.ADVERTISEMENT, Decimal("0")))
        penalties = abs(sums.get(LedgerOperationType.PENALTY, Decimal("0")))
        acquiring = abs(sums.get(LedgerOperationType.ACQUIRING, Decimal("0")))
        deductions = abs(sums.get(LedgerOperationType.DEDUCTION, Decimal("0")))
        compensation = sums.get(LedgerOperationType.COMPENSATION, Decimal("0"))

        payout_actual = sums.get(LedgerOperationType.PAYOUT, Decimal("0"))

        # Profit for the period from economics projection (sum of contribution margin).
        econ_stmt = select(
            func.coalesce(func.sum(SkuUnitEconomicsDaily.cogs), 0),
            func.coalesce(func.sum(SkuUnitEconomicsDaily.contribution_margin), 0),
        ).where(
            SkuUnitEconomicsDaily.marketplace == marketplace,
            SkuUnitEconomicsDaily.metric_date >= period.start,
            SkuUnitEconomicsDaily.metric_date <= period.end,
        )
        econ_res = await self.execute_with_rls(econ_stmt)
        cogs_sum, profit_sum = econ_res.one()
        cogs = Decimal(cogs_sum)
        profit = Decimal(profit_sum)

        expected_payout_value = expected_payout(
            revenue=revenue,
            returns_amount=returns_amount,
            commissions=commissions,
            logistics=logistics,
            storage=storage,
            ads=ads,
            penalties=penalties,
            acquiring=acquiring,
            deductions=deductions,
            compensation=compensation,
        )
        payout_diff = payout_actual - expected_payout_value

        warnings: list[IntegrityWarning] = []
        if revenue < 0:
            warnings.append(
                IntegrityWarning(
                    code="negative_revenue",
                    severity="critical",
                    message="Обнаружена отрицательная выручка за период (ошибка нормализации знаков).",
                )
            )
        if abs(payout_diff) > Decimal("0"):
            warnings.append(
                IntegrityWarning(
                    code="payout_mismatch",
                    severity="warning",
                    message="Фактические выплаты не совпадают с расчётными по компонентам (возможна неполная загрузка отчётов/компонентов).",
                    context={"difference": str(payout_diff)},
                )
            )

        explanation = (
            "Выплата (к перечислению) — это движение денег (cashflow) от маркетплейса к продавцу. "
            "Прибыль — это экономический результат продаж: выручка минус возвраты, комиссии, логистика, хранение, реклама, штрафы и СЕБЕСТОИМОСТЬ (COGS). "
            "Поэтому выплата почти никогда не равна прибыли."
        )

        return ReconciliationResponse(
            marketplace=marketplace,
            period_start=period.start,
            period_end=period.end,
            breakdown=ReconciliationBreakdown(
                revenue=revenue,
                returns_amount=returns_amount,
                commissions=commissions,
                logistics=logistics,
                storage=storage,
                ads=ads,
                penalties=penalties,
                acquiring=acquiring,
                deductions=deductions,
                compensation=compensation,
                cogs=cogs,
                expected_payout=expected_payout_value,
                actual_payout=payout_actual,
                payout_difference=payout_diff,
                profit=profit,
                payout_is_not_profit_explanation=explanation,
            ),
            freshness=freshness,
            warnings=warnings,
        )

