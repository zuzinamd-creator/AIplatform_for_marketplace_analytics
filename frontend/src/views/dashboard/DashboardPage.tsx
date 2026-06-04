import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Bot, Database, LineChart as LineChartIcon, Server, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { api } from "../../state/http";
import { loadWorkspaceProfile } from "../../state/onboarding";
import { isDemoMode } from "../../state/settings";
import { trackUsage } from "../../state/usage";
import { CHART } from "../../ui/chart-theme";
import { Card } from "../../ui/card";
import { CollapsibleSection } from "../../ui/collapsible-section";
import { KpiCard } from "../../ui/kpi-card";
import { StatusBadge } from "../../ui/status-badge";
import { PeriodSelector } from "../../ui/period-selector";
import { loadPeriodSelection, previousPeriod, type PeriodSelection } from "../../state/period";
import { toast } from "../../ui/toast";
import { FirstRunChecklist } from "../../ui/first-run-checklist";

export function DashboardPage() {
  useEffect(() => {
    trackUsage("view_dashboard");
  }, []);

  const demo = isDemoMode();
  const workspace = loadWorkspaceProfile();
  const marketplace = workspace.marketplace === "unknown" ? "wildberries" : workspace.marketplace;
  const [periodSel, setPeriodSel] = useState<PeriodSelection>(() => loadPeriodSelection());
  const start = periodSel.range.start;
  const end = periodSel.range.end;
  const compare = useMemo(() => {
    if (!periodSel.compareEnabled) return null;
    if (periodSel.comparePreset === "custom" && periodSel.compareRange) return periodSel.compareRange;
    return previousPeriod(periodSel.range);
  }, [periodSel]);
  const queue = useQuery({
    queryKey: ["ops", "queue", 0, 10],
    queryFn: () => api.ops.queue(0, 10),
  });
  const runtime = useQuery({
    queryKey: ["ops", "runtimeSummary"],
    queryFn: () => api.ops.runtimeSummary(),
  });
  const aiOps = useQuery({
    queryKey: ["ai", "ops"],
    queryFn: () => api.ai.operationalStatus(),
  });
  const todaysFocus = useQuery({
    queryKey: ["ai", "todaysFocus"],
    queryFn: () => api.ai.todaysFocus(),
  });
  const recommendations = useQuery({
    queryKey: ["ai", "recommendations", 0, 5],
    queryFn: () => api.ai.recommendations(0, 5),
  });
  const runAiPeriod = useQuery({
    enabled: false,
    queryKey: ["ai", "periodRun", marketplace, start, end],
    queryFn: async () => {
      return await api.ai.runIntelligenceForPeriod({
        workflow: "revenue_insight",
        prompt_id: "analytics.summary.v1",
        semantics_version: "1.0",
        marketplace,
        period_start: start,
        period_end: end,
      });
    },
  });
  const kpiSummary = useQuery({
    queryKey: ["analytics", "revenueSummary", marketplace, start, end],
    queryFn: () => api.analytics.revenueSummary({ marketplace, start, end }),
  });
  const kpiSummaryCompare = useQuery({
    enabled: !!compare,
    queryKey: ["analytics", "revenueSummary", "compare", marketplace, compare?.start, compare?.end],
    queryFn: () =>
      api.analytics.revenueSummary({ marketplace, start: compare!.start, end: compare!.end }),
  });
  const kpiTrend = useQuery({
    queryKey: ["analytics", "revenueTrendDaily", marketplace, start, end],
    queryFn: () => api.analytics.revenueTrendDaily({ marketplace, start, end }),
  });
  const financeSummary = useQuery({
    queryKey: ["analytics", "financeSummary", marketplace, start, end],
    queryFn: () => api.analytics.financialSummary({ marketplace, start, end }),
  });
  const financeTrend = useQuery({
    queryKey: ["analytics", "financeTrendDaily", marketplace, start, end],
    queryFn: () => api.analytics.financialTrendDaily({ marketplace, start, end }),
  });
  const topSkus = useQuery({
    queryKey: ["analytics", "topSkus", marketplace, start, end],
    queryFn: () => api.analytics.topSkus({ marketplace, start, end, limit: 5, sort: "revenue" }),
  });
  const coverage = useQuery({
    queryKey: ["analytics", "coverage"],
    queryFn: () => api.analytics.coverage(),
  });

  const statusCounts = queue.data?.status_counts ?? {};
  const queued = Object.values(statusCounts).reduce((a, b) => a + b, 0);
  const recCount = (recommendations.data as { items?: unknown[] })?.items?.length ?? 0;
  const rebuild = ((runtime.data as Record<string, unknown>)?.rebuild ?? {}) as Record<string, number>;
  const freshness = kpiSummary.data?.freshness;
  const stale = freshness?.stale_data_warning ?? false;
  const integrityWarnings = kpiSummary.data?.integrity?.warnings ?? [];
  const completeness = kpiSummary.data?.integrity?.financial_completeness_score ?? null;
  const aRevenue = Number(kpiSummary.data?.kpis.total_revenue ?? "0");
  const bRevenue = Number(kpiSummaryCompare.data?.kpis.total_revenue ?? "0");
  const deltaRevenue = compare ? aRevenue - bRevenue : null;
  const pct = (delta: number, base: number) => (base !== 0 ? (delta / base) * 100 : null);

  return (
    <div className="page-shell">
      <FirstRunChecklist />
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="page-title">Финансовая аналитика продавца</h1>
            {demo ? (
              <StatusBadge tone="info">
                <Sparkles className="mr-1 inline h-3 w-3" />
                Демо
              </StatusBadge>
            ) : null}
          </div>
          <p className="page-subtitle">Периодная аналитика с прозрачностью, полнотой и предупреждениями.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            className="btn-primary"
            to="/app/reports/upload"
            onClick={() => trackUsage("cta_upload")}
          >
            Загрузить отчёт
          </Link>
          <Link className="btn-secondary" to="/app/ai/recommendations">
            Рекомендации ИИ
          </Link>
          <button
            className="btn-accent"
            onClick={async () => {
              try {
                const res = await runAiPeriod.refetch();
                toast("ИИ-анализ периода запущен", res.data?.summary ?? "Готово.");
              } catch (e) {
                toast("ИИ-анализ не запустился", e instanceof Error ? e.message : "Неизвестная ошибка");
              }
            }}
          >
            ИИ-анализ периода
          </button>
        </div>
      </div>

      <PeriodSelector onChange={setPeriodSel} />

      <CollapsibleSection
        title="Что требует внимания сегодня"
        subtitle="Ежедневное рабочее место продавца: риски, утечки прибыли, задачи и доверие к данным."
        actions={<Link to="/app/today" className="link-muted">Брифинг «Сегодня» →</Link>}
      >
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Card className="p-4">
            <div className="text-xs font-medium text-ink-muted">Критические проблемы</div>
            <div className="mt-2 text-sm text-ink-secondary">
              {(todaysFocus.data?.dangerous ?? []).slice(0, 3).join(" · ") || "Нет критичных флагов."}
            </div>
          </Card>
          <Card className="p-4">
            <div className="text-xs font-medium text-ink-muted">Утечки прибыли</div>
            <div className="mt-2 text-sm text-ink-secondary">
              Проверьте маржу и затраты по SKU в экономике.
            </div>
            <Link to="/app/finance/reconciliation" className="link-muted mt-3 inline-block text-xs">
              Сверка выплат →
            </Link>
          </Card>
          <Card className="p-4">
            <div className="text-xs font-medium text-ink-muted">Доверие к марже</div>
            <div className="mt-2 text-sm text-ink-secondary">
              {completeness ? `Полнота аналитики: ${completeness}%` : "Полнота неизвестна"}
              {(aiOps.data as any)?.degraded_intelligence_mode ? " · ИИ осторожен" : ""}
            </div>
            <Link to="/app/finance/costs" className="link-muted mt-3 inline-block text-xs">
              Покрытие затрат →
            </Link>
          </Card>
        </div>
      </CollapsibleSection>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <div className="lg:col-span-5">
          <KpiCard
            variant="hero"
            icon={<Database className="h-5 w-5" />}
            label="Продажи (выбранный период)"
            value={kpiSummary.isLoading ? "…" : (kpiSummary.data?.kpis.total_revenue ?? "0")}
            sub={
              <span>
                Валовая прибыль: {kpiSummary.data?.kpis.total_profit ?? "0"} · Маржинальность:{" "}
                {kpiSummary.data?.kpis.margin_pct ?? "—"}% {stale ? "· данные устарели" : ""}
                {compare && deltaRevenue !== null ? (
                  <>
                    {" "}
                    · Δвыручка: {deltaRevenue.toFixed(0)}{" "}
                    {pct(deltaRevenue, bRevenue) !== null ? `(${pct(deltaRevenue, bRevenue)!.toFixed(1)}%)` : ""}
                  </>
                ) : null}
              </span>
            }
          />
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 lg:col-span-7">
          <KpiCard
            icon={<Server className="h-4 w-4" />}
            label="Обработка данных"
            value={queue.isLoading ? "…" : queued}
            sub={<span>Задач в очереди/обработке</span>}
          />
          <KpiCard
            icon={<Bot className="h-4 w-4" />}
            label="Рекомендации ИИ"
            value={recommendations.isLoading ? "…" : recCount}
            sub={
              <span>
                {(aiOps.data as Record<string, unknown>)?.degraded_intelligence_mode
                  ? "Осторожный режим"
                  : "Обычный режим"}
              </span>
            }
          />
          <KpiCard
            icon={<AlertTriangle className="h-4 w-4" />}
            label="Обновление аналитики"
            value={runtime.isLoading ? "…" : (rebuild.running ?? 0) + (rebuild.pending_dispatch ?? 0)}
            sub={<span>Пересборки активны или в очереди</span>}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card className="p-6 md:col-span-2">
          <div className="flex items-center justify-between gap-3">
            <div className="text-sm font-semibold text-ink">Тренд продаж и прибыли (по дням)</div>
            <StatusBadge tone={stale ? "warn" : "info"}>
              <LineChartIcon className="mr-1 inline h-3 w-3" />
              {stale ? "устарело" : "актуально"}
            </StatusBadge>
          </div>
          <div className="chart-panel mt-5">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={(kpiTrend.data?.points ?? []).map((p) => ({
                  date: p.date.slice(5),
                  revenue: Number(p.revenue),
                  profit: Number(p.net_profit),
                }))}
              >
                <XAxis dataKey="date" tick={CHART.axis} />
                <YAxis tick={CHART.axis} />
                <Tooltip contentStyle={CHART.tooltip} />
                <Line type="monotone" dataKey="revenue" stroke={CHART.series.revenue} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="profit" stroke={CHART.series.profit} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 text-xs text-ink-muted">
            Данные проанализированы за период: {start} → {end} · Последнее обновление: {freshness?.data_as_of ?? "—"}
            {completeness ? <> · Полнота аналитики: {completeness}%</> : null}
          </div>
          {integrityWarnings.length ? (
            <div className="mt-4 rounded-xl border border-amber-200 bg-semantic-warn-bg p-4 text-xs text-semantic-warn">
              <div className="font-semibold">Предупреждения целостности</div>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {integrityWarnings.slice(0, 4).map((w) => (
                  <li key={w.code}>{w.message}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </Card>

        <Card className="p-6">
          <div className="text-sm font-semibold text-ink">Топ SKU по продажам</div>
          <div className="mt-2 text-xs text-ink-muted">
            Период: {start} → {end} · {marketplace}
          </div>
          <div className="mt-5 space-y-3">
            {(topSkus.data?.items ?? []).length === 0 ? (
              <div className="text-sm text-ink-muted">Пока нет метрик по SKU.</div>
            ) : (
              (topSkus.data?.items ?? []).map((row) => (
                <div key={row.sku} className="flex items-center justify-between gap-3 border-b border-surface-subtle/60 pb-2 last:border-0 last:pb-0">
                  <div className="truncate text-sm font-medium text-ink-secondary">{row.sku}</div>
                  <div className="text-right text-xs text-ink-muted">
                    {row.revenue}
                    <div className="text-[11px] text-ink-faint">
                      {row.contribution_pct ? `Доля: ${row.contribution_pct}%` : "—"}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
          <div className="mt-5 space-y-2 text-xs text-ink-muted">
            <div>
              Диапазон данных: {coverage.data?.available_min_date ?? "—"} → {coverage.data?.available_max_date ?? "—"}
            </div>
            {(coverage.data?.missing_periods ?? []).length ? (
              <div>Есть пропуски в периодах: {coverage.data?.missing_periods.length}</div>
            ) : null}
            {(coverage.data?.recommendations ?? []).length ? (
              <div>Рекомендации: {coverage.data?.recommendations.length}</div>
            ) : null}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card className="p-6 md:col-span-2">
          <div className="text-sm font-semibold text-ink">Затраты и возвраты (по дням)</div>
          <div className="chart-panel mt-5">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={(financeTrend.data?.points ?? []).map((p) => ({
                  date: p.date.slice(5),
                  logistics: Number(p.logistics),
                  ads: Number(p.advertisement),
                  returns: Number(p.returns_amount),
                  payout: Number(p.payout),
                }))}
              >
                <XAxis dataKey="date" tick={CHART.axis} />
                <YAxis tick={CHART.axis} />
                <Tooltip contentStyle={CHART.tooltip} />
                <Line type="monotone" dataKey="logistics" stroke={CHART.series.logistics} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="ads" stroke={CHART.series.ads} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="returns" stroke={CHART.series.returns} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="payout" stroke={CHART.series.payout} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 text-xs text-ink-muted">
            Логистика · Продвижение · Возвраты · Выплаты
          </div>
        </Card>

        <Card className="p-6">
          <div className="text-sm font-semibold text-ink">Финансовая сводка</div>
          <div className="mt-2 text-xs text-ink-muted">Период: {start} → {end}</div>
          <div className="mt-5 space-y-2.5 text-sm text-ink-secondary">
            <div className="flex justify-between gap-3"><span>Продажа, руб.</span><span>{financeSummary.data?.kpis.sales_revenue ?? "—"}</span></div>
            <div className="flex justify-between gap-3"><span>Возвраты, руб.</span><span>{financeSummary.data?.kpis.returns_amount ?? "—"}</span></div>
            <div className="flex justify-between gap-3"><span>Стоимость логистики, руб.</span><span>{financeSummary.data?.kpis.logistics ?? "—"}</span></div>
            <div className="flex justify-between gap-3"><span>Затраты на продвижение, руб.</span><span>{financeSummary.data?.kpis.advertisement ?? "—"}</span></div>
            <div className="flex justify-between gap-3"><span>Штрафы, руб.</span><span>{financeSummary.data?.kpis.penalties ?? "—"}</span></div>
            <div className="flex justify-between gap-3"><span>Хранение, руб.</span><span>{financeSummary.data?.kpis.storage_fee ?? "—"}</span></div>
            <div className="flex justify-between gap-3"><span>К перечислению, руб.</span><span>{financeSummary.data?.kpis.payout ?? "—"}</span></div>
            <div className="mt-3 flex justify-between gap-3 border-t border-surface-subtle pt-3 font-semibold text-ink">
              <span>Валовая прибыль, руб.</span><span>{financeSummary.data?.kpis.gross_profit ?? "—"}</span>
            </div>
            <div className="flex justify-between gap-3">
              <span>Маржинальность, %</span><span>{financeSummary.data?.kpis.margin_pct ?? "—"}</span>
            </div>
            <div className="flex justify-between gap-3">
              <span>Процент возвратов</span><span>{financeSummary.data?.kpis.return_rate_pct ?? "—"}%</span>
            </div>
          </div>
          <div className="mt-4 text-xs text-ink-muted">
            Некоторые показатели могут быть неполными, если не загружены нужные отчёты или себестоимость.
          </div>
        </Card>
      </div>

      <CollapsibleSection
        title="Ежедневный сценарий и доверие к данным"
        subtitle="Справочные блоки для регулярной работы с аналитикой."
      >
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <div>
            <div className="text-sm font-semibold text-ink">Ежедневный сценарий</div>
            <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-relaxed text-ink-secondary">
              <li>Загрузите свежий отчёт (если есть)</li>
              <li>
                Проверьте <Link className="link-muted" to="/app/status">статус системы</Link> (очередь/пересборки)
              </li>
              <li>
                Откройте <Link className="link-muted" to="/app/ai/recommendations">входящие ИИ</Link> или{" "}
                <Link className="link-muted" to="/app/ai/today">фокус на сегодня</Link>
                {" · "}
                <Link className="link-muted" to="/app/ai/digest?type=daily">ежедневный дайджест</Link>
              </li>
              <li>Сохраните/отклоните рекомендации и оставьте обратную связь</li>
            </ol>
          </div>
          <div>
            <div className="text-sm font-semibold text-ink">Доверие к данным</div>
            <p className="mt-3 text-sm leading-relaxed text-ink-secondary">
              Финансовые KPI берутся из read-only аналитического слоя. Если данные устарели — проверьте пересборки и очередь;
              в режиме устаревания трактуйте выводы ИИ осторожно.
            </p>
            <Link to="/app/onboarding" className="link-muted mt-4 inline-block text-sm">
              Завершить настройку →
            </Link>
          </div>
        </div>
      </CollapsibleSection>

      {demo ? (
        <Card className="border-sky-200 bg-brand-subtle p-6">
          <div className="text-sm font-semibold text-brand">Демо-сценарий</div>
          <p className="mt-2 text-sm leading-relaxed text-ink-secondary">
            1) Загрузка отчёта → 2) Обработка → 3) Рекомендация ИИ → 4) Объяснимость → 5) Действие и оценка полезности.
          </p>
          <Link to="/app/support" className="link-muted mt-3 inline-block text-sm">
            Отладка демо →
          </Link>
        </Card>
      ) : null}
    </div>
  );
}
