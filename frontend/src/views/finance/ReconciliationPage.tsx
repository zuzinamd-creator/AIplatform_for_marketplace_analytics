import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "../../state/http";
import { loadWorkspaceProfile } from "../../state/onboarding";
import { loadPeriodSelection } from "../../state/period";
import {
  COSTS_WORKFLOW_ROUTE,
  COST_COVERAGE_ROUTE,
  formatProfitValue,
  showInlineCostTrustBanner,
  useProfitTrust,
  type ProfitTrustContext,
} from "../../state/profit-trust";
import { formatRub } from "../../utils/format";
import { Card } from "../../ui/card";
import { CollapsibleSection } from "../../ui/collapsible-section";
import { CostTrustBanner } from "../../ui/cost-trust-banner";
import { KpiCard } from "../../ui/kpi-card";
import { PeriodSelector } from "../../ui/period-selector";
import { ProfitTrustBadge } from "../../ui/profit-trust-badge";
import { StatusBadge } from "../../ui/status-badge";
import { WarnCallout } from "../../ui/warn-callout";

function Row(props: { label: string; value: unknown; trustValue?: boolean; trust?: ProfitTrustContext }) {
  const display =
    props.trustValue && props.trust
      ? formatProfitValue(props.value, props.trust.trust)
      : formatRub(props.value);
  return (
    <div className="flex items-center justify-between gap-3 border-t border-surface-subtle py-2.5 text-sm">
      <div className="text-ink-secondary">{props.label}</div>
      <div className="font-medium text-ink">{display}</div>
    </div>
  );
}

export function ReconciliationPage() {
  const workspace = loadWorkspaceProfile();
  const marketplace = workspace.marketplace === "unknown" ? "wildberries" : workspace.marketplace;
  const initial = loadPeriodSelection();
  const [range, setRange] = useState(() => initial.range);

  const rec = useQuery({
    queryKey: ["analytics", "reconciliationPeriod", marketplace, range.start, range.end],
    queryFn: () => api.analytics.reconciliationPeriod({ marketplace, start: range.start, end: range.end }),
  });

  const revenue = useQuery({
    queryKey: ["analytics", "revenueSummary", "reconciliation", marketplace, range.start, range.end],
    queryFn: () => api.analytics.revenueSummary({ marketplace, start: range.start, end: range.end }),
  });

  const costCoverage = useQuery({
    queryKey: ["analytics", "costCoverage", "reconciliation", marketplace, range.start, range.end],
    queryFn: () => api.analytics.costCoverage({ marketplace, start: range.start, end: range.end, limit: 1 }),
  });

  const trustCtx = useProfitTrust(revenue.data?.integrity, costCoverage.data ?? null);

  const stale = rec.data?.freshness?.stale_data_warning ?? false;
  const w = rec.data?.warnings ?? [];
  const b = rec.data?.breakdown;

  return (
    <div className="page-shell">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h1 className="page-title">Финансовая сверка</h1>
          <p className="page-subtitle">
            Справочный разбор компонентов периода. В MVP автоматическое сравнение выплат с expected_payout
            отключено — колонка WB «К перечислению» использует базу расчёта со скидками (СПП), отличную от
            «Цена розничная − комиссия».
          </p>
        </div>
        <StatusBadge tone={stale ? "warn" : "info"}>{stale ? "данные устарели" : "актуально"}</StatusBadge>
      </div>

      <PeriodSelector onChange={(s) => setRange(s.range)} />

      {showInlineCostTrustBanner() && trustCtx.trust !== "full" ? (
        <CostTrustBanner
          trust={trustCtx.trust}
          variant="inline"
          coveragePct={trustCtx.coveragePct}
          coveredSkus={trustCtx.coveredSkus}
          totalSkus={trustCtx.totalSkus}
          missingSkusSample={trustCtx.missingSkus.slice(0, 5)}
          storageKey={`reconciliation-${range.start}-${range.end}`}
        />
      ) : null}

      {b ? (
        <div className="kpi-row md:grid-cols-3">
          <KpiCard variant="hero" label="Фактическая выплата" value={formatRub(b.actual_payout)} />
          <KpiCard
            label={
              <span className="inline-flex flex-wrap items-center gap-2">
                Прибыль (contribution)
                <ProfitTrustBadge trust={trustCtx.trust} trustContext={trustCtx} metric="profit" />
              </span>
            }
            value={formatProfitValue(b.profit, trustCtx.trust)}
          />
          <KpiCard label="Разница выплат" value={formatRub(b.payout_difference)} />
        </div>
      ) : null}

      {w.length ? (
        <WarnCallout title="Предупреждения">
          <ul className="list-disc space-y-1 pl-5">
            {w.map((x) => (
              <li key={x.code}>{x.message}</li>
            ))}
          </ul>
        </WarnCallout>
      ) : null}

      <CollapsibleSection title="Компоненты периода" subtitle="Детальный разбор статей" defaultOpen>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Card className="p-5">
          <div className="text-sm font-semibold">Компоненты периода</div>
          <div className="mt-2 text-xs text-ink-muted">
            Период: {range.start} → {range.end} · Маркетплейс: {marketplace}
          </div>
          {b ? (
            <div className="mt-4">
              <Row label="Выручка" value={b.revenue} />
              <Row label="Возвраты" value={b.returns_amount} />
              <Row label="Комиссии" value={b.commissions} />
              <Row label="Логистика" value={b.logistics} />
              <Row label="Хранение" value={b.storage} />
              <Row label="Реклама" value={b.ads} />
              <Row label="Штрафы" value={b.penalties} />
              <Row label="Эквайринг" value={b.acquiring} />
              <Row label="Удержания" value={b.deductions} />
              <Row label="Компенсации" value={b.compensation} />
              <Row label="COGS (себестоимость)" value={b.cogs} />
              <div className="mt-3 border-t border-surface-subtle pt-3">
                <Row label="Расчётная выплата" value={b.expected_payout} />
                <Row label="Фактическая выплата" value={b.actual_payout} />
                <Row label="Разница выплат" value={b.payout_difference} />
                <Row label="Прибыль (contribution margin)" value={b.profit} trustValue trust={trustCtx} />
              </div>
            </div>
          ) : (
            <div className="mt-4 text-sm text-ink-muted">{rec.isLoading ? "Загрузка…" : "Нет данных."}</div>
          )}
        </Card>

        <Card className="p-4">
          <div className="text-sm font-semibold">Почему выплата ≠ прибыль</div>
          <div className="mt-3 text-sm text-ink-secondary">
            {b?.payout_is_not_profit_explanation ?? "—"}
          </div>
          <div className="mt-4 rounded-lg border border-surface-subtle bg-surface-inset p-3 text-xs text-ink-secondary">
            {trustCtx.trust === "insufficient"
              ? "Прибыль недоступна без себестоимости. Загрузите cost-данные для contribution margin."
              : trustCtx.trust === "partial"
                ? "Прибыль показана как оценка — себестоимость указана не для всех SKU."
                : "Прибыль проверена при полном покрытии себестоимости."}
          </div>
          <div className="mt-3 flex flex-wrap gap-3 text-xs">
            <Link to={COSTS_WORKFLOW_ROUTE} className="link-muted">
              Себестоимость →
            </Link>
            <Link to={COST_COVERAGE_ROUTE} className="link-muted">
              Покрытие себестоимости →
            </Link>
          </div>
        </Card>
      </div>
      </CollapsibleSection>
    </div>
  );
}
