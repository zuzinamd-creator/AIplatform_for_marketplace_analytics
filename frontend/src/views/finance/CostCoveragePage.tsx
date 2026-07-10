import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "../../state/http";
import { loadWorkspaceProfile } from "../../state/onboarding";
import { loadPeriodSelection } from "../../state/period";
import {
  COSTS_WORKFLOW_ROUTE,
  normalizeProfitTrust,
  showInlineCostTrustBanner,
  useProfitTrust,
} from "../../state/profit-trust";
import { formatInteger, formatPct, formatRub } from "../../utils/format";
import { Card } from "../../ui/card";
import { CollapsibleSection } from "../../ui/collapsible-section";
import { CostCoverageIndicator } from "../../ui/cost-coverage-indicator";
import { CostTrustBanner } from "../../ui/cost-trust-banner";
import { KpiCard } from "../../ui/kpi-card";
import { PeriodSelector } from "../../ui/period-selector";
import { Input, Label } from "../../ui/field";
import { ProfitTrustBadge } from "../../ui/profit-trust-badge";
import { StatusBadge } from "../../ui/status-badge";
import { WarnCallout } from "../../ui/warn-callout";

export function CostCoveragePage() {
  const workspace = loadWorkspaceProfile();
  const marketplace = workspace.marketplace === "unknown" ? "wildberries" : workspace.marketplace;
  const initial = loadPeriodSelection();
  const [range, setRange] = useState(() => initial.range);
  const [q, setQ] = useState("");

  const coverage = useQuery({
    queryKey: ["analytics", "costCoverage", marketplace, range.start, range.end, q],
    queryFn: () => api.analytics.costCoverage({ marketplace, start: range.start, end: range.end, q: q || undefined }),
  });

  const revenue = useQuery({
    queryKey: ["analytics", "revenueSummary", "costCoveragePage", marketplace, range.start, range.end],
    queryFn: () => api.analytics.revenueSummary({ marketplace, start: range.start, end: range.end }),
  });

  const trustCtx = useProfitTrust(revenue.data?.integrity, coverage.data ?? null);

  const score = coverage.data?.cost_completeness_score ?? null;
  const covPct = coverage.data?.sku_cost_coverage_pct ?? null;
  const stale = coverage.data?.freshness?.stale_data_warning ?? false;
  const topWarnings = useMemo(() => coverage.data?.warnings ?? [], [coverage.data]);

  return (
    <div className="page-shell">
      <div className="flex items-end justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="page-title">Покрытие себестоимости</h1>
            <ProfitTrustBadge trust={trustCtx.trust} trustContext={trustCtx} metric="profit" />
          </div>
          <p className="page-subtitle">
            Доля продаваемых SKU с загруженной себестоимостью. Определяет уровень доверия к прибыли и марже на dashboard и в аналитике.
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
          storageKey={`cost-coverage-page-${range.start}-${range.end}`}
        />
      ) : null}

      {trustCtx.coveredSkus !== null && trustCtx.totalSkus !== null ? (
        <CostCoverageIndicator
          coveredSkus={trustCtx.coveredSkus}
          totalSkus={trustCtx.totalSkus}
          coveragePct={trustCtx.coveragePct}
          variant="bar"
          showCta={trustCtx.trust !== "full"}
        />
      ) : null}

      <div className="kpi-row md:grid-cols-2">
        <KpiCard
          variant="hero"
          label="Готовность расчёта прибыли"
          value={formatPct(score)}
          sub="С учётом заполненности себестоимости и предупреждений"
        />
        <KpiCard
          label={
            <span className="inline-flex flex-wrap items-center gap-2">
              Товаров с себестоимостью
              <ProfitTrustBadge trust={trustCtx.trust} trustContext={trustCtx} metric="profit" showLabel={false} />
            </span>
          }
          value={
            covPct !== null && coverage.data
              ? `${coverage.data.covered_skus} из ${coverage.data.total_skus} (${formatPct(covPct)})`
              : formatPct(covPct)
          }
          sub={`Trust: ${normalizeProfitTrust(revenue.data?.integrity?.profit_metrics_trust)}`}
        />
      </div>

      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <Label>Фильтр по SKU</Label>
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="например: SKU-123" className="mt-2 max-w-md" />
            <p className="mt-2 text-xs text-ink-muted">SKU с продажами в выбранном периоде.</p>
          </div>
          <Link to={COSTS_WORKFLOW_ROUTE} className="btn-secondary h-9 px-3 text-xs">
            Загрузить себестоимость
          </Link>
        </div>
      </Card>

      {topWarnings.length ? (
        <WarnCallout title="Предупреждения">
          <ul className="list-disc space-y-1 pl-5">
            {topWarnings.map((w) => (
              <li key={w.code}>{w.message}</li>
            ))}
          </ul>
        </WarnCallout>
      ) : null}

      <CollapsibleSection title="SKU с продажами" subtitle="Покрытие себестоимостью по строкам" defaultOpen>
      <Card className="border-0 p-0 shadow-none">
        <div className="text-sm font-semibold">SKU с продажами (покрытие себестоимостью)</div>
        <div className="mt-2 text-xs text-ink-muted">
          Период: {range.start} → {range.end} · Маркетплейс: {marketplace}
        </div>
        <div className="mt-4 overflow-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-xs text-ink-muted">
              <tr>
                <th className="py-2 pr-4">SKU</th>
                <th className="py-2 pr-4">Продано</th>
                <th className="py-2 pr-4">Выручка</th>
                <th className="py-2 pr-4">Себестоимость</th>
                <th className="py-2 pr-4">Покрытие</th>
                <th className="py-2 pr-4">Последняя дата</th>
              </tr>
            </thead>
            <tbody className="text-ink-secondary">
              {(coverage.data?.items ?? []).map((row) => (
                <tr key={row.sku} className="border-t border-surface-subtle">
                  <td className="py-2 pr-4">{row.sku}</td>
                  <td className="py-2 pr-4">{formatInteger(row.units_sold)}</td>
                  <td className="py-2 pr-4">{formatRub(row.revenue)}</td>
                  <td className="py-2 pr-4">{formatRub(row.cogs)}</td>
                  <td className="py-2 pr-4">{formatPct(row.cost_coverage_pct)}</td>
                  <td className="py-2 pr-4">{row.last_cost_effective_from ?? "—"}</td>
                </tr>
              ))}
              {coverage.isLoading ? (
                <tr>
                  <td className="py-3 text-ink-muted" colSpan={6}>
                    Загрузка…
                  </td>
                </tr>
              ) : null}
              {!coverage.isLoading && (coverage.data?.items ?? []).length === 0 ? (
                <tr>
                  <td className="py-3 text-ink-muted" colSpan={6}>
                    Нет данных за выбранный период.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </Card>
      </CollapsibleSection>
    </div>
  );
}
