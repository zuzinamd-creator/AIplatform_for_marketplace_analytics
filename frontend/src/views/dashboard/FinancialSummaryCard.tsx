import { Card } from "../../ui/card";
import { ProfitTrustBadge } from "../../ui/profit-trust-badge";
import {
  formatMarginValue,
  formatProfitValue,
  formatProfitabilityValue,
  type ProfitTrustContext,
} from "../../state/profit-trust";
import { formatRub } from "../../utils/format";
import type { FinancialKpiSummaryResponse } from "../../state/types-analytics";

type FinanceKpis = FinancialKpiSummaryResponse["kpis"];

export type FinancialSummaryCardProps = {
  periodStart: string;
  periodEnd: string;
  totalRevenue: string | null | undefined;
  financeKpis: FinanceKpis | null | undefined;
  trustCtx: ProfitTrustContext;
};

/**
 * Behavior-freeze extract of the dashboard «Финансовая сводка» card (Phase 9.9-R18).
 * No UX/label/order changes — presentation only.
 */
export function FinancialSummaryCard({
  periodStart,
  periodEnd,
  totalRevenue,
  financeKpis,
  trustCtx,
}: FinancialSummaryCardProps) {
  const wbPromotionExpenses = Number(financeKpis?.promotion_expenses ?? "0");
  const jamSubscriptionExpenses = Number(financeKpis?.jam_subscription_expenses ?? "0");
  const manualExpensesTotal = Number(
    financeKpis?.manual_expenses_total ?? wbPromotionExpenses + jamSubscriptionExpenses,
  );
  const hasManualExpenses = manualExpensesTotal > 0;

  return (
    <Card className="p-6">
      <div className="flex flex-wrap items-center gap-2">
        <div className="text-sm font-semibold text-ink">Финансовая сводка</div>
        <ProfitTrustBadge trust={trustCtx.trust} trustContext={trustCtx} metric="profit" />
      </div>
      <div className="mt-2 text-xs text-ink-muted">
        Период: {periodStart} → {periodEnd}
      </div>
      <div className="mt-5 space-y-2.5 text-sm text-ink-secondary">
        <div className="flex justify-between gap-3">
          <span>Выручка</span>
          <span>{formatRub(totalRevenue)}</span>
        </div>
        <div className="flex justify-between gap-3">
          <span>К перечислению за товар</span>
          <span>{formatRub(financeKpis?.payout_for_goods ?? financeKpis?.payout)}</span>
        </div>
        <div className="flex justify-between gap-3">
          <span>Логистика</span>
          <span>{formatRub(financeKpis?.logistics)}</span>
        </div>
        <div className="flex justify-between gap-3">
          <span>Хранение</span>
          <span>{formatRub(financeKpis?.storage_fee)}</span>
        </div>
        <div className="flex justify-between gap-3">
          <span>Удержания</span>
          <span>{formatRub(financeKpis?.deductions)}</span>
        </div>
        {wbPromotionExpenses > 0 ? (
          <div className="flex justify-between gap-3 pl-3 text-ink-muted">
            <span>в т.ч. WB-продвижение</span>
            <span>{formatRub(financeKpis?.promotion_expenses)}</span>
          </div>
        ) : null}
        {jamSubscriptionExpenses > 0 ? (
          <div className="flex justify-between gap-3 pl-3 text-ink-muted">
            <span>в т.ч. Подписка Джем</span>
            <span>{formatRub(financeKpis?.jam_subscription_expenses)}</span>
          </div>
        ) : null}
        <div className="flex justify-between gap-3 border-t border-surface-subtle pt-2">
          <span>Settlement WB (к перечислению)</span>
          <span>{formatRub(financeKpis?.total_to_pay)}</span>
        </div>
        <div className="flex justify-between gap-3">
          <span>Себестоимость</span>
          <span>{formatRub(financeKpis?.cogs)}</span>
        </div>
        <div className="mt-3 flex justify-between gap-3 border-t border-surface-subtle pt-3 font-semibold text-ink">
          <span className="inline-flex items-center gap-2">
            Чистая прибыль
            <ProfitTrustBadge trust={trustCtx.trust} trustContext={trustCtx} metric="profit" showLabel={false} />
          </span>
          <span>{formatProfitValue(financeKpis?.gross_profit, trustCtx.trust)}</span>
        </div>
        <div className="flex justify-between gap-3">
          <span className="inline-flex items-center gap-2">
            Маржинальность
            <ProfitTrustBadge trust={trustCtx.trust} metric="margin" showLabel={false} />
          </span>
          <span>{formatMarginValue(financeKpis?.margin_pct, trustCtx.trust)}</span>
        </div>
        <div className="flex justify-between gap-3">
          <span>Рентабельность</span>
          <span>{formatProfitabilityValue(financeKpis?.profitability_pct, trustCtx.trust)}</span>
        </div>
      </div>
      <div className="mt-4 space-y-2 text-xs text-ink-muted">
        {hasManualExpenses ? (
          <div>
            Чистая прибыль = Settlement WB − себестоимость. WB-продвижение и Джем — детализация
            удержаний (уже внутри Settlement), без повторного вычета.
          </div>
        ) : null}
        {trustCtx.trust === "insufficient"
          ? "Прибыль и маржа недоступны без себестоимости."
          : trustCtx.trust === "partial"
            ? "Прибыль показана как оценка; маржа скрыта при неполном покрытии COGS."
            : "Показатели проверены при полном покрытии себестоимости."}
      </div>
    </Card>
  );
}
