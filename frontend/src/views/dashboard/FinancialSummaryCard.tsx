import type { ReactNode } from "react";
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

function MetricRow({
  label,
  value,
  emphasize,
  className = "",
}: {
  label: ReactNode;
  value: ReactNode;
  emphasize?: "primary" | "secondary";
  className?: string;
}) {
  const rowTone =
    emphasize === "primary"
      ? "font-semibold text-ink text-[0.95rem]"
      : emphasize === "secondary"
        ? "font-semibold text-ink"
        : "text-ink-secondary";
  return (
    <div className={`flex justify-between gap-3 ${rowTone} ${className}`.trim()}>
      <span className="inline-flex items-center gap-2">{label}</span>
      <span>{value}</span>
    </div>
  );
}

function InlineDisclosure({
  summary,
  children,
}: {
  summary: string;
  children: ReactNode;
}) {
  return (
    <details className="group text-ink-muted">
      <summary className="cursor-pointer list-none text-xs hover:text-ink-secondary [&::-webkit-details-marker]:hidden">
        <span className="inline-flex items-center gap-1">
          <span aria-hidden className="select-none group-open:hidden">
            ▸
          </span>
          <span aria-hidden className="hidden select-none group-open:inline">
            ▾
          </span>
          {summary}
        </span>
      </summary>
      <div className="mt-2 space-y-2 pl-3 text-sm">{children}</div>
    </details>
  );
}

/**
 * Financial summary card (Phase 9.9-R19 UX): two blocks, disclosures, seller-facing labels.
 * Data sources and profit math are unchanged — presentation only.
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
  const hasDeductionBreakdown = wbPromotionExpenses > 0 || jamSubscriptionExpenses > 0;

  return (
    <Card className="p-6">
      <div className="flex flex-wrap items-center gap-2">
        <div className="text-sm font-semibold text-ink">Финансовая сводка</div>
        <ProfitTrustBadge trust={trustCtx.trust} trustContext={trustCtx} metric="profit" />
      </div>
      <div className="mt-2 text-xs text-ink-muted">
        Период: {periodStart} → {periodEnd}
      </div>

      <div className="mt-5 space-y-5">
        {/* Block 1: money from WB */}
        <section className="space-y-2.5 text-sm">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
            Деньги от Wildberries
          </h3>
          <MetricRow label="Выручка" value={formatRub(totalRevenue)} />
          <MetricRow
            label="К перечислению за товар"
            value={formatRub(financeKpis?.payout_for_goods ?? financeKpis?.payout)}
          />
          <InlineDisclosure summary="Детализация услуг WB">
            <MetricRow label="Логистика" value={formatRub(financeKpis?.logistics)} />
            <MetricRow label="Хранение" value={formatRub(financeKpis?.storage_fee)} />
          </InlineDisclosure>
          <div className="space-y-2">
            <MetricRow label="Удержания WB" value={formatRub(financeKpis?.deductions)} />
            {hasDeductionBreakdown ? (
              <InlineDisclosure summary="Из них">
                {wbPromotionExpenses > 0 ? (
                  <MetricRow
                    label="WB-продвижение"
                    value={formatRub(financeKpis?.promotion_expenses)}
                  />
                ) : null}
                {jamSubscriptionExpenses > 0 ? (
                  <MetricRow
                    label="Подписка Джем"
                    value={formatRub(financeKpis?.jam_subscription_expenses)}
                  />
                ) : null}
              </InlineDisclosure>
            ) : null}
          </div>
          <MetricRow
            label="Выплата от WB"
            value={formatRub(financeKpis?.total_to_pay)}
            emphasize="secondary"
            className="border-t border-surface-subtle pt-2"
          />
        </section>

        {/* Block 2: profit */}
        <section className="space-y-2.5 text-sm">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">Прибыль</h3>
          <MetricRow label="Себестоимость" value={formatRub(financeKpis?.cogs)} />
          <MetricRow
            label={
              <>
                Чистая прибыль
                <ProfitTrustBadge
                  trust={trustCtx.trust}
                  trustContext={trustCtx}
                  metric="profit"
                  showLabel={false}
                />
              </>
            }
            value={formatProfitValue(financeKpis?.gross_profit, trustCtx.trust)}
            emphasize="primary"
            className="border-t border-surface-subtle pt-3"
          />
          <MetricRow
            label={
              <>
                Маржа
                <ProfitTrustBadge trust={trustCtx.trust} metric="margin" showLabel={false} />
              </>
            }
            value={formatMarginValue(financeKpis?.margin_pct, trustCtx.trust)}
          />
          <InlineDisclosure summary="Ещё показатели">
            <MetricRow
              label="Рентабельность"
              value={formatProfitabilityValue(financeKpis?.profitability_pct, trustCtx.trust)}
            />
          </InlineDisclosure>
        </section>
      </div>

      <div className="mt-4 space-y-2 text-xs text-ink-muted">
        <div>Выплата от WB − Себестоимость = Чистая прибыль</div>
        {trustCtx.trust === "insufficient"
          ? "Прибыль и маржа недоступны без себестоимости."
          : trustCtx.trust === "partial"
            ? "Прибыль показана как оценка; маржа скрыта при неполном покрытии COGS."
            : "Показатели проверены при полном покрытии себестоимости."}
      </div>
    </Card>
  );
}
