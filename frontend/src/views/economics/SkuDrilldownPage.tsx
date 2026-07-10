import { useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowLeft, AlertTriangle, Info } from "lucide-react";

import { api } from "../../state/http";
import { loadWorkspaceProfile } from "../../state/onboarding";
import {
  formatProfitValue,
  formatDeltaWithTrust,
  showInlineCostTrustBanner,
  useProfitTrust,
} from "../../state/profit-trust";
import {
  chartPctTooltip,
  chartRubTooltip,
  formatMetric,
  formatPct,
  formatRub,
} from "../../utils/format";
import { CHART } from "../../ui/chart-theme";
import { Card } from "../../ui/card";
import { CollapsibleSection } from "../../ui/collapsible-section";
import { CostTrustBanner } from "../../ui/cost-trust-banner";
import { Select } from "../../ui/field";
import { KpiCard } from "../../ui/kpi-card";
import { PeriodSelector } from "../../ui/period-selector";
import { ProfitTrustBadge } from "../../ui/profit-trust-badge";
import { loadPeriodSelection, previousPeriod, type PeriodSelection } from "../../state/period";
import { StatusBadge } from "../../ui/status-badge";

function explainLoss(
  points: Array<{ gross_profit: string; revenue: string; logistics: string; ads: string; penalties: string; returns_amount: string }>,
  trust: "full" | "partial" | "insufficient",
) {
  if (trust === "insufficient") {
    return "Недостаточно данных для оценки прибыльности — загрузите себестоимость по этому SKU.";
  }
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
  if (profit >= 0) {
    return trust === "partial"
      ? "Прибыль показана как оценка (не у всех SKU указана себестоимость). Смотрите логистику, рекламу и возвраты."
      : "Товар прибыльный в выбранный период. Смотрите, что можно улучшить по логистике/рекламе/возвратам.";
  }
  const profitLabel = trust === "partial" ? `оценочная прибыль ${formatProfitValue(profit, trust)}` : `прибыль ${formatRub(profit)}`;
  return `Товар убыточен: ${profitLabel} при выручке ${formatRub(rev)}. Сильнее всего съедает прибыль: ${top ? `${top.k} (${formatRub(top.v)})` : "затраты/возвраты"}.`;
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

  const costCoverage = useQuery({
    queryKey: ["analytics", "costCoverage", marketplace, start, end],
    queryFn: () => api.analytics.costCoverage({ marketplace, start, end, limit: 1 }),
  });

  const trustCtx = useProfitTrust(a.data?.integrity, costCoverage.data ?? null);

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

      {showInlineCostTrustBanner() && trustCtx.trust !== "full" ? (
        <CostTrustBanner
          trust={trustCtx.trust}
          variant="inline"
          coveragePct={trustCtx.coveragePct}
          coveredSkus={trustCtx.coveredSkus}
          totalSkus={trustCtx.totalSkus}
          missingSkusSample={trustCtx.missingSkus.slice(0, 5)}
          storageKey={`sku-${sku}-${start}-${end}`}
        />
      ) : null}

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
                Полнота: {formatMetric(integrity.financial_completeness_score)} / 100
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

      <div className="kpi-row">
        <KpiCard variant="hero" label="Выручка" value={formatRub(kpis.rev)} sub={compare ? `Δ ${formatRub(kpis.rev - kpis.revB)}` : undefined} />
        <KpiCard
          label={
            <span className="inline-flex flex-wrap items-center gap-2">
              Валовая прибыль
              <ProfitTrustBadge trust={trustCtx.trust} trustContext={trustCtx} metric="profit" />
            </span>
          }
          value={formatProfitValue(kpis.profit, trustCtx.trust)}
          sub={
            compare && trustCtx.canShowProfit
              ? `Δ ${formatDeltaWithTrust(kpis.profit - kpis.profitB, trustCtx.trust, "rub")}`
              : undefined
          }
        />
        <KpiCard
          label={
            <span className="inline-flex flex-wrap items-center gap-2">
              Маржинальный вклад
              <ProfitTrustBadge trust={trustCtx.trust} trustContext={trustCtx} metric="profit" />
            </span>
          }
          value={formatProfitValue(kpis.cm, trustCtx.trust)}
          sub={
            compare && trustCtx.canShowProfit
              ? `Δ ${formatDeltaWithTrust(kpis.cm - kpis.cmB, trustCtx.trust, "rub")}`
              : undefined
          }
        />
        <KpiCard
          label={
            <span className="inline-flex flex-wrap items-center gap-2">
              Маржа
              <ProfitTrustBadge trust={trustCtx.trust} metric="margin" />
            </span>
          }
          value={trustCtx.canShowMargin ? formatPct(kpis.margin) : "—"}
          sub={
            compare && trustCtx.canShowMargin && kpis.marginB !== null && kpis.margin !== null
              ? `Δ ${formatDeltaWithTrust(kpis.margin - kpis.marginB, trustCtx.trust, "pct")}`
              : undefined
          }
        />
      </div>

      <Card className="p-4">
        <div className="text-sm font-semibold">Почему товар убыточен</div>
        <div className="mt-2 text-sm text-ink-secondary">{explainLoss(points, trustCtx.trust)}</div>
        <div className="mt-3 flex items-start gap-2 text-xs text-ink-muted">
          <Info className="mt-0.5 h-4 w-4" />
          <div>
            “Валовая прибыль” зависит от себестоимости. Если себестоимость отсутствует, прибыль и маржа могут быть искажены — это будет видно в предупреждениях.
          </div>
        </div>
      </Card>

      <CollapsibleSection title="Графики по дням" subtitle="Выручка, затраты, маржа и возвраты" defaultOpen>
      {trustCtx.trust !== "full" ? (
        <p className="mb-3 text-xs text-ink-muted">
          {trustCtx.trust === "insufficient"
            ? "График прибыли недоступен без себестоимости."
            : "Прибыль на графике — оценка; маржа скрыта при неполном покрытии себестоимости."}
        </p>
      ) : null}
      <div className="grid gap-3 lg:grid-cols-2">
        <Card className="p-4">
          <div className="section-title">Выручка vs прибыль</div>
          <div className="chart-panel mt-3">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <XAxis dataKey="date" hide />
                <YAxis hide />
                <Tooltip contentStyle={CHART.tooltip} formatter={chartRubTooltip} />
                <Line type="monotone" dataKey="revenue" stroke={CHART.series.revenue} strokeWidth={2} dot={false} />
                {trustCtx.canShowProfit ? (
                  <Line type="monotone" dataKey="profit" stroke={CHART.series.profit} strokeWidth={2} dot={false} strokeDasharray={trustCtx.trust === "partial" ? "4 4" : undefined} />
                ) : null}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-4">
          <div className="section-title">Логистика vs реклама vs штрафы</div>
          <div className="chart-panel mt-3">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <XAxis dataKey="date" hide />
                <YAxis hide />
                <Tooltip contentStyle={CHART.tooltip} formatter={chartRubTooltip} />
                <Line type="monotone" dataKey="logistics" stroke={CHART.series.logistics} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="ads" stroke={CHART.series.ads} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="penalties" stroke={CHART.series.returns} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {trustCtx.canShowMargin ? (
        <Card className="p-4">
          <div className="section-title">Маржа (дневная)</div>
          <div className="chart-panel mt-3">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <XAxis dataKey="date" hide />
                <YAxis hide />
                <Tooltip contentStyle={CHART.tooltip} formatter={chartPctTooltip} />
                <Line type="monotone" dataKey="margin" stroke={CHART.series.profit} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
        ) : (
        <Card className="p-4">
          <div className="section-title">Маржа (дневная)</div>
          <div className="mt-3 flex h-[180px] items-center justify-center text-sm text-ink-muted">
            Маржа недоступна — загрузите себестоимость для всех SKU.
          </div>
        </Card>
        )}

        <Card className="p-4">
          <div className="section-title">Возвраты (динамика)</div>
          <div className="chart-panel mt-3">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <XAxis dataKey="date" hide />
                <YAxis hide />
                <Tooltip contentStyle={CHART.tooltip} formatter={chartRubTooltip} />
                <Line type="monotone" dataKey="returns" stroke={CHART.series.returns} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
      </CollapsibleSection>

      <Card className="p-4">
        <div className="section-title">Что ухудшилось относительно прошлого периода</div>
        {compare && trustCtx.canShowProfit ? (
          <div className="mt-2 text-sm text-ink-secondary">
            Прибыль: {formatProfitValue(kpis.profit, trustCtx.trust)} (Δ {formatDeltaWithTrust(kpis.profit - kpis.profitB, trustCtx.trust, "rub")}), выручка: {formatRub(kpis.rev)} (Δ{" "}
            {formatRub(kpis.rev - kpis.revB)}), маржа: {trustCtx.canShowMargin ? formatPct(kpis.margin) : "—"}{" "}
            {trustCtx.canShowMargin && kpis.marginB !== null && kpis.margin !== null
              ? `(Δ ${formatDeltaWithTrust(kpis.margin - kpis.marginB, trustCtx.trust, "pct")})`
              : ""}.
          </div>
        ) : compare ? (
          <div className="mt-2 text-sm text-ink-muted">Сравнение прибыли недоступно без себестоимости.</div>
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

