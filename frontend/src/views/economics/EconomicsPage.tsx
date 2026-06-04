import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Line, LineChart, ResponsiveContainer, Tooltip, YAxis } from "recharts";
import { Filter, Search, TrendingUp } from "lucide-react";

import { api } from "../../state/http";
import { loadWorkspaceProfile } from "../../state/onboarding";
import { CHART } from "../../ui/chart-theme";
import { Card } from "../../ui/card";
import { Input, Select } from "../../ui/field";
import { PeriodSelector } from "../../ui/period-selector";
import { loadPeriodSelection, previousPeriod, type PeriodSelection } from "../../state/period";
import { StatusBadge } from "../../ui/status-badge";

function rub(v: string | number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  const n = typeof v === "number" ? v : Number(v);
  if (!Number.isFinite(n)) return String(v);
  return n.toLocaleString("ru-RU", { maximumFractionDigits: 0 }) + " ₽";
}

function pct(v: string | null | undefined): string {
  if (!v) return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString("ru-RU", { maximumFractionDigits: 1 }) + " %";
}

function badgeForSku(row: {
  contribution_margin: string;
  margin_pct?: string | null;
  return_rate?: string | null;
}): { label: string; tone: "ok" | "warn" | "bad" | "info" } {
  const cm = Number(row.contribution_margin);
  const m = row.margin_pct ? Number(row.margin_pct) : null;
  const rr = row.return_rate ? Number(row.return_rate) : null;
  if (Number.isFinite(cm) && cm < 0) return { label: "Убыточный", tone: "bad" };
  if (m !== null && Number.isFinite(m) && m < 5) return { label: "Низкая маржа", tone: "warn" };
  if (rr !== null && Number.isFinite(rr) && rr >= 20) return { label: "Риск (возвраты)", tone: "warn" };
  return { label: "Прибыльный", tone: "ok" };
}

function integrityBanner(integrity?: { warnings: Array<{ code: string; severity: string; message: string }>; financial_completeness_score?: string | null } | null) {
  const warnings = integrity?.warnings ?? [];
  const score = integrity?.financial_completeness_score ?? null;
  const critical = warnings.filter((w) => w.severity === "critical");
  const warning = warnings.filter((w) => w.severity === "warning");
  if (!warnings.length && !score) return null;
  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="text-sm font-semibold text-ink">Доверие к данным</div>
          <div className="mt-1 text-xs text-ink-muted">
            {score ? `Полнота: ${Number(score).toLocaleString("ru-RU", { maximumFractionDigits: 0 })} / 100` : "Полнота: —"}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {critical.length ? <StatusBadge tone="bad">Критические предупреждения: {critical.length}</StatusBadge> : null}
          {warning.length ? <StatusBadge tone="warn">Предупреждения: {warning.length}</StatusBadge> : null}
          {!critical.length && !warning.length ? <StatusBadge tone="info">Нет предупреждений</StatusBadge> : null}
        </div>
      </div>
      {warnings.length ? (
        <ul className="mt-3 space-y-1 text-xs text-ink-secondary">
          {warnings.slice(0, 4).map((w) => (
            <li key={w.code + w.message}>- {w.message}</li>
          ))}
          {warnings.length > 4 ? <li>— и ещё {warnings.length - 4}</li> : null}
        </ul>
      ) : null}
      <div className="mt-3 text-xs text-ink-muted">
        ИИ может быть неточным, если отсутствует себестоимость или есть расхождения выплат. В таком случае рекомендации показываются с пониженной уверенностью.
      </div>
    </Card>
  );
}

export function EconomicsPage() {
  const workspace = loadWorkspaceProfile();
  const defaultMarketplace = workspace.marketplace === "unknown" ? "wildberries" : workspace.marketplace;
  const [marketplace, setMarketplace] = useState<string>(defaultMarketplace);
  const [periodSel, setPeriodSel] = useState<PeriodSelection>(() => loadPeriodSelection());
  const [q, setQ] = useState("");
  const [sort, setSort] = useState("contribution_margin");
  const [order, setOrder] = useState<"asc" | "desc">("desc");

  const start = periodSel.range.start;
  const end = periodSel.range.end;
  const compare = useMemo(() => {
    if (!periodSel.compareEnabled) return null;
    if (periodSel.comparePreset === "custom" && periodSel.compareRange) return periodSel.compareRange;
    return previousPeriod(periodSel.range);
  }, [periodSel]);

  const a = useQuery({
    queryKey: ["analytics", "skuEconomics", marketplace, start, end, q, sort, order],
    queryFn: () =>
      api.analytics.skuEconomics({
        marketplace,
        start,
        end,
        skip: 0,
        limit: 50,
        q: q.trim() ? q.trim() : undefined,
        sort,
        order,
      }),
  });

  const b = useQuery({
    enabled: !!compare,
    queryKey: ["analytics", "skuEconomics", "compare", marketplace, compare?.start, compare?.end, q, sort, order],
    queryFn: () =>
      api.analytics.skuEconomics({
        marketplace,
        start: compare!.start,
        end: compare!.end,
        skip: 0,
        limit: 50,
        q: q.trim() ? q.trim() : undefined,
        sort,
        order,
      }),
  });

  const topSkusForSparklines = useMemo(() => (a.data?.items ?? []).slice(0, 10).map((r) => r.sku), [a.data]);
  const sparklines = topSkusForSparklines.map((sku) =>
    useQuery({
      enabled: !!sku && !!a.data,
      queryKey: ["analytics", "skuDrilldown", marketplace, start, end, sku],
      queryFn: () => api.analytics.skuDrilldown({ marketplace, start, end, sku }),
      staleTime: 60_000,
    }),
  );
  const sparkBySku = useMemo(() => {
    const m = new Map<string, Array<{ x: string; y: number }>>();
    sparklines.forEach((q) => {
      const sku = q.data?.sku;
      if (!sku) return;
      const pts = (q.data?.points ?? []).map((p) => ({ x: p.date, y: Number(p.gross_profit) }));
      m.set(sku, pts);
    });
    return m;
  }, [sparklines]);

  const compareBySku = useMemo(() => {
    const m = new Map<string, { cm: number; m: number | null }>();
    (b.data?.items ?? []).forEach((r) => {
      m.set(r.sku, { cm: Number(r.contribution_margin), m: r.margin_pct ? Number(r.margin_pct) : null });
    });
    return m;
  }, [b.data]);

  return (
    <div className="page-shell">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="page-title">Экономика товаров</h1>
          <p className="page-subtitle">Прибыльность, маржа и то, что «съедает» прибыль по SKU.</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Select
            value={marketplace}
            onChange={(e) => setMarketplace(e.target.value)}
            className="h-9 w-auto min-w-[10rem]"
          >
            <option value="wildberries">Wildberries</option>
            <option value="ozon">Ozon</option>
          </Select>
        </div>
      </div>

      <PeriodSelector onChange={setPeriodSel} />

      {integrityBanner(a.data?.integrity ?? null)}

      <Card className="overflow-hidden p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-sm font-medium text-ink-secondary">
            <Filter className="h-4 w-4 text-ink-muted" /> Фильтры
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-ink-faint" />
              <Input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Поиск по SKU…"
                className="h-9 w-64 pl-9"
              />
            </div>
            <Select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              className="h-9 w-auto min-w-[11rem]"
            >
              <option value="contribution_margin">Маржинальный вклад</option>
              <option value="gross_profit">Валовая прибыль</option>
              <option value="revenue">Выручка</option>
              <option value="margin_pct">Маржа %</option>
              <option value="returns">Возвраты</option>
              <option value="ads">Реклама</option>
              <option value="return_rate">Доля возвратов</option>
            </Select>
            <button type="button" onClick={() => setOrder((o) => (o === "asc" ? "desc" : "asc"))} className="btn-secondary h-9">
              {order === "asc" ? "По возрастанию" : "По убыванию"}
            </button>
          </div>
        </div>

        <div className="mt-5 overflow-auto rounded-xl border border-surface-subtle">
          <table className="table-shell w-full min-w-[1100px] text-sm">
            <thead className="text-left">
              <tr>
                <th className="py-2">SKU</th>
                <th className="py-2">Статус</th>
                <th className="py-2">Выручка</th>
                <th className="py-2">Валовая прибыль</th>
                <th className="py-2">Маржинальный вклад</th>
                <th className="py-2">Маржа</th>
                <th className="py-2">Логистика</th>
                <th className="py-2">Реклама</th>
                <th className="py-2">Штрафы</th>
                <th className="py-2">Возвраты</th>
                <th className="py-2">Тренд прибыли</th>
              </tr>
            </thead>
            <tbody>
              {(a.data?.items ?? []).map((r) => {
                const bRow = compareBySku.get(r.sku);
                const status = badgeForSku(r);
                const spark = sparkBySku.get(r.sku) ?? [];
                return (
                  <tr key={r.sku}>
                    <td className="px-3 py-3 font-medium">
                      <Link to={`/app/economics/sku/${encodeURIComponent(r.sku)}`} className="text-ink-secondary hover:text-brand hover:underline">
                        {r.sku}
                      </Link>
                    </td>
                    <td className="px-3 py-3">
                      <StatusBadge tone={status.tone}>{status.label}</StatusBadge>
                    </td>
                    <td className="px-3 py-3">{rub(r.revenue)}</td>
                    <td className="px-3 py-3">{rub(r.gross_profit)}</td>
                    <td className="px-3 py-3">
                      <div className="flex items-center gap-2">
                        <span>{rub(r.contribution_margin)}</span>
                        {compare ? (
                          <span className="text-xs text-ink-muted">
                            Δ {rub(Number(r.contribution_margin) - (bRow?.cm ?? 0))}
                          </span>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex items-center gap-2">
                        <span>{pct(r.margin_pct ?? null)}</span>
                        {compare && bRow?.m !== null ? (
                          <span className="text-xs text-ink-muted">Δ {(Number(r.margin_pct ?? 0) - (bRow?.m ?? 0)).toFixed(1)}%</span>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-3 py-3">{rub(r.logistics)}</td>
                    <td className="px-3 py-3">{rub(r.ads)}</td>
                    <td className="px-3 py-3">{rub(r.penalties)}</td>
                    <td className="px-3 py-3">{rub(r.returns_amount)}</td>
                    <td className="py-2 w-[180px]">
                      <div className="h-10 w-[170px]">
                        {spark.length ? (
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={spark}>
                              <YAxis hide domain={["auto", "auto"]} />
                              <Tooltip
                                contentStyle={CHART.tooltip}
                                labelFormatter={() => ""}
                                formatter={(value: unknown) => [rub(Number(value)), "Прибыль"]}
                              />
                              <Line type="monotone" dataKey="y" stroke={CHART.series.spark} strokeWidth={2} dot={false} />
                            </LineChart>
                          </ResponsiveContainer>
                        ) : (
                          <div className="flex h-full items-center gap-2 text-xs text-ink-faint">
                            <TrendingUp className="h-4 w-4" /> —
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {!a.isLoading && !(a.data?.items?.length ?? 0) ? (
                <tr>
                  <td className="px-3 py-8 text-center text-ink-muted" colSpan={11}>
                    Нет данных по SKU за выбранный период. Проверьте период и загрузку отчетов.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>

        <div className="mt-5 text-xs leading-relaxed text-ink-muted">
          <span className="font-medium text-ink-secondary">Пояснение:</span> выплата — это денежный поток, прибыль — это P&amp;L (выручка минус возвраты и затраты). Если есть предупреждение “расхождение выплат”, используйте экран сверки выплат.
          <div className="mt-2">
            <Link to="/app/finance/reconciliation" className="link-muted inline-flex items-center gap-2">
              Перейти к “Финансовая сверка”
            </Link>
          </div>
        </div>
      </Card>
    </div>
  );
}

