import { useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowLeft, AlertTriangle, Info } from "lucide-react";

import { api } from "../../state/http";
import { loadWorkspaceProfile } from "../../state/onboarding";
import { CHART } from "../../ui/chart-theme";
import { Card } from "../../ui/card";
import { Select } from "../../ui/field";
import { KpiCard } from "../../ui/kpi-card";
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

function deltaLabel(a: number, b: number): string {
  const d = a - b;
  const sign = d > 0 ? "+" : "";
  return sign + d.toLocaleString("ru-RU", { maximumFractionDigits: 1 });
}

function explainLoss(points: Array<{ gross_profit: string; revenue: string; logistics: string; ads: string; penalties: string; returns_amount: string }>) {
  const sum = (key: keyof (typeof points)[number]) => points.reduce((acc, p) => acc + Number(p[key] ?? 0), 0);
  const profit = sum("gross_profit");
  const rev = sum("revenue");
  const drivers = [
    { k: "Возвраты", v: sum("returns_amount") },
    { k: "Логистика", v: sum("logistics") },
    { k: "Реклама", v: sum("ads") },
    { k: "Штрафы", v: sum("penalties") },
  ].sort((a, b) => b.v - a.v);

  const top = drivers.find((d) => d.v > 0);
  if (rev <= 0) return "Нет выручки в выбранный период — проверьте отчёты или период.";
  if (profit >= 0) return "Товар прибыльный в выбранный период. Смотрите, что можно улучшить по логистике/рекламе/возвратам.";
  return `Товар убыточен: прибыль ${rub(profit)} при выручке ${rub(rev)}. Сильнее всего съедает прибыль: ${top ? `${top.k} (${rub(top.v)})` : "затраты/возвраты"}.`;
}

export function SkuDrilldownPage() {
  const params = useParams();
  const sku = decodeURIComponent(params.sku ?? "");

  const workspace = loadWorkspaceProfile();
  const defaultMarketplace = workspace.marketplace === "unknown" ? "wildberries" : workspace.marketplace;
  const [marketplace, setMarketplace] = useState<string>(defaultMarketplace);
  const [periodSel, setPeriodSel] = useState<PeriodSelection>(() => loadPeriodSelection());

  const start = periodSel.range.start;
  const end = periodSel.range.end;
  const compare = useMemo(() => {
    if (!periodSel.compareEnabled) return null;
    if (periodSel.comparePreset === "custom" && periodSel.compareRange) return periodSel.compareRange;
    return previousPeriod(periodSel.range);
  }, [periodSel]);

  const a = useQuery({
    queryKey: ["analytics", "skuDrilldown", marketplace, start, end, sku],
    queryFn: () => api.analytics.skuDrilldown({ marketplace, start, end, sku }),
  });
  const b = useQuery({
    enabled: !!compare,
    queryKey: ["analytics", "skuDrilldown", "compare", marketplace, compare?.start, compare?.end, sku],
    queryFn: () => api.analytics.skuDrilldown({ marketplace, start: compare!.start, end: compare!.end, sku }),
  });

  const points = a.data?.points ?? [];
  const pointsB = b.data?.points ?? [];

  const sum = (arr: typeof points, key: keyof (typeof points)[number]) =>
    arr.reduce((acc, p) => acc + Number(p[key] ?? 0), 0);
  const kpis = useMemo(() => {
    const rev = sum(points, "revenue");
    const profit = sum(points, "gross_profit");
    const cm = sum(points, "contribution_margin");
    const margin = rev > 0 ? (profit / rev) * 100 : null;
    const revB = sum(pointsB, "revenue");
    const profitB = sum(pointsB, "gross_profit");
    const cmB = sum(pointsB, "contribution_margin");
    const marginB = revB > 0 ? (profitB / revB) * 100 : null;
    return { rev, profit, cm, margin, revB, profitB, cmB, marginB };
  }, [points, pointsB]);

  const chartData = useMemo(
    () =>
      points.map((p) => ({
        date: p.date,
        revenue: Number(p.revenue),
        profit: Number(p.gross_profit),
        margin: p.margin_pct ? Number(p.margin_pct) : null,
        returns: Number(p.returns_amount),
        logistics: Number(p.logistics),
        ads: Number(p.ads),
        penalties: Number(p.penalties),
        stock: p.stock_units ?? null,
      })),
    [points],
  );

  const integrity = a.data?.integrity ?? null;
  const warnings = integrity?.warnings ?? [];
  const critical = warnings.filter((w) => w.severity === "critical");

  return (
    <div className="page-shell">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <Link to="/app/economics" className="inline-flex items-center gap-2 text-sm text-ink-muted hover:text-brand hover:underline">
            <ArrowLeft className="h-4 w-4" /> Назад к списку
          </Link>
          <h1 className="page-title mt-3">SKU: {sku}</h1>
          <p className="page-subtitle">Глубокий разбор: прибыль, маржа, возвраты, затраты и склад.</p>
        </div>
        <Select
          value={marketplace}
          onChange={(e) => setMarketplace(e.target.value)}
          className="h-9 w-auto min-w-[10rem]"
        >
          <option value="wildberries">Wildberries</option>
          <option value="ozon">Ozon</option>
        </Select>
      </div>

      <PeriodSelector onChange={setPeriodSel} />

      {warnings.length ? (
        <Card className="p-4">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <AlertTriangle className="h-4 w-4 text-semantic-warn" />
            Доверие к данным
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {critical.length ? <StatusBadge tone="bad">Критично: {critical.length}</StatusBadge> : null}
            {warnings.filter((w) => w.severity === "warning").length ? (
              <StatusBadge tone="warn">Предупреждения: {warnings.filter((w) => w.severity === "warning").length}</StatusBadge>
            ) : null}
            {integrity?.financial_completeness_score ? (
              <StatusBadge tone="info">
                Полнота: {Number(integrity.financial_completeness_score).toLocaleString("ru-RU", { maximumFractionDigits: 0 })} / 100
              </StatusBadge>
            ) : null}
          </div>
          <ul className="mt-3 space-y-1 text-xs text-ink-secondary">
            {warnings.slice(0, 6).map((w) => (
              <li key={w.code + w.message}>- {w.message}</li>
            ))}
          </ul>
          <div className="mt-3 text-xs text-ink-muted">
            ИИ может быть неточным, потому что: {warnings.slice(0, 2).map((w) => w.message).join("; ")}
          </div>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Выручка" value={rub(kpis.rev)} sub={compare ? `Δ ${rub(kpis.rev - kpis.revB)}` : undefined} variant="compact" />
        <KpiCard label="Валовая прибыль" value={rub(kpis.profit)} sub={compare ? `Δ ${rub(kpis.profit - kpis.profitB)}` : undefined} variant="compact" />
        <KpiCard label="Маржинальный вклад" value={rub(kpis.cm)} sub={compare ? `Δ ${rub(kpis.cm - kpis.cmB)}` : undefined} variant="compact" />
        <KpiCard
          label="Маржа"
          value={kpis.margin === null ? "—" : `${kpis.margin.toFixed(1)} %`}
          sub={compare && kpis.marginB !== null && kpis.margin !== null ? `Δ ${deltaLabel(kpis.margin, kpis.marginB)}%` : undefined}
          variant="compact"
        />
      </div>

      <Card className="p-4">
        <div className="text-sm font-semibold">Почему товар убыточен</div>
        <div className="mt-2 text-sm text-ink-secondary">{explainLoss(points)}</div>
        <div className="mt-3 flex items-start gap-2 text-xs text-ink-muted">
          <Info className="mt-0.5 h-4 w-4" />
          <div>
            “Валовая прибыль” зависит от себестоимости. Если себестоимость отсутствует, прибыль и маржа могут быть искажены — это будет видно в предупреждениях.
          </div>
        </div>
      </Card>

      <div className="grid gap-3 lg:grid-cols-2">
        <Card className="p-4">
          <div className="text-sm font-semibold">Выручка vs прибыль</div>
          <div className="mt-3 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <XAxis dataKey="date" hide />
                <YAxis hide />
                <Tooltip contentStyle={CHART.tooltip} formatter={(value: unknown, name: string) => [rub(Number(value)), name]} />
                <Line type="monotone" dataKey="revenue" stroke={CHART.series.revenue} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="profit" stroke={CHART.series.profit} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-4">
          <div className="text-sm font-semibold">Логистика vs реклама vs штрафы</div>
          <div className="mt-3 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <XAxis dataKey="date" hide />
                <YAxis hide />
                <Tooltip contentStyle={CHART.tooltip} formatter={(value: unknown, name: string) => [rub(Number(value)), name]} />
                <Line type="monotone" dataKey="logistics" stroke={CHART.series.logistics} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="ads" stroke={CHART.series.ads} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="penalties" stroke={CHART.series.returns} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-4">
          <div className="text-sm font-semibold">Маржа (дневная)</div>
          <div className="mt-3 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <XAxis dataKey="date" hide />
                <YAxis hide />
                <Tooltip contentStyle={CHART.tooltip} formatter={(value: unknown) => [pct(String(value)), "Маржа"]} />
                <Line type="monotone" dataKey="margin" stroke={CHART.series.profit} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-4">
          <div className="text-sm font-semibold">Возвраты (динамика)</div>
          <div className="mt-3 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <XAxis dataKey="date" hide />
                <YAxis hide />
                <Tooltip contentStyle={CHART.tooltip} formatter={(value: unknown) => [rub(Number(value)), "Возвраты"]} />
                <Line type="monotone" dataKey="returns" stroke={CHART.series.returns} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card className="p-4">
        <div className="text-sm font-semibold">Что ухудшилось относительно прошлого периода</div>
        {compare ? (
          <div className="mt-2 text-sm text-ink-secondary">
            Прибыль: {rub(kpis.profit)} (Δ {rub(kpis.profit - kpis.profitB)}), выручка: {rub(kpis.rev)} (Δ {rub(kpis.rev - kpis.revB)}), маржа:{" "}
            {kpis.margin === null ? "—" : `${kpis.margin.toFixed(1)}%`}{" "}
            {kpis.marginB === null || kpis.margin === null ? "" : `(Δ ${deltaLabel(kpis.margin, kpis.marginB)}%)`}.
          </div>
        ) : (
          <div className="mt-2 text-sm text-ink-muted">Включите сравнение периодов в селекторе периода, чтобы увидеть, что изменилось.</div>
        )}
      </Card>

      <Card className="p-4">
        <div className="text-sm font-semibold">Рекомендации и уверенность ИИ</div>
        <div className="mt-2 text-sm text-ink-muted">
          Рекомендации по SKU берутся из общей ленты рекомендаций. Если есть предупреждения по данным (себестоимость/выплаты), приоритизация и уверенность ИИ автоматически понижаются.
        </div>
        <div className="mt-3">
          <Link to="/app/ai/recommendations" className="link-muted">
            Открыть рекомендации
          </Link>
        </div>
      </Card>

      {a.isLoading ? <div className="text-sm text-ink-muted">Загрузка…</div> : null}
      {a.error ? <div className="text-sm text-red-300">Ошибка загрузки SKU.</div> : null}
    </div>
  );
}

