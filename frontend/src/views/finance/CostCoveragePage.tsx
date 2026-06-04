import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "../../state/http";
import { loadWorkspaceProfile } from "../../state/onboarding";
import { loadPeriodSelection } from "../../state/period";
import { Card } from "../../ui/card";
import { PeriodSelector } from "../../ui/period-selector";
import { Input, Label } from "../../ui/field";
import { StatusBadge } from "../../ui/status-badge";

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

  const score = coverage.data?.cost_completeness_score ?? null;
  const covPct = coverage.data?.sku_cost_coverage_pct ?? null;
  const stale = coverage.data?.freshness?.stale_data_warning ?? false;

  const topWarnings = useMemo(() => coverage.data?.warnings ?? [], [coverage.data]);

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-3">
        <div>
          <div className="text-2xl font-semibold">Себестоимость и покрытие затрат</div>
          <div className="text-sm text-ink-secondary">
            Понимание, можно ли доверять марже: полнота COGS, дубли, устаревшие стоимости.
          </div>
        </div>
        <StatusBadge tone={stale ? "warn" : "info"}>{stale ? "данные устарели" : "актуально"}</StatusBadge>
      </div>

      <PeriodSelector onChange={(s) => setRange(s.range)} />

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <Card className="p-4">
          <div className="text-xs text-ink-secondary">Полнота затрат (score)</div>
          <div className="mt-1 text-xl font-semibold">{score ?? "—"}%</div>
          <div className="mt-1 text-xs text-ink-muted">Эвристика на основе покрытия SKU + предупреждений.</div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-ink-secondary">Покрытие SKU себестоимостью</div>
          <div className="mt-1 text-xl font-semibold">{covPct ?? "—"}%</div>
          <div className="mt-1 text-xs text-ink-muted">
            SKU считаются покрытыми, если COGS &gt; 0 при наличии продаж.
          </div>
        </Card>
        <Card className="p-4">
          <Label>Фильтр по SKU</Label>
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="например: SKU-123" />
          <div className="mt-2 text-xs text-ink-muted">Показывает SKU с продажами в выбранном периоде.</div>
        </Card>
      </div>

      {topWarnings.length ? (
        <Card className="border-amber-500/30 bg-amber-500/10 p-4">
          <div className="text-sm font-semibold text-amber-100">Предупреждения</div>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-100">
            {topWarnings.map((w) => (
              <li key={w.code}>{w.message}</li>
            ))}
          </ul>
        </Card>
      ) : null}

      <Card className="p-4">
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
                  <td className="py-2 pr-4">{row.units_sold}</td>
                  <td className="py-2 pr-4">{row.revenue}</td>
                  <td className="py-2 pr-4">{row.cogs}</td>
                  <td className="py-2 pr-4">{row.cost_coverage_pct ?? "—"}%</td>
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
    </div>
  );
}

