import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Bot, Database, LineChart as LineChartIcon, Server, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { api } from "../../state/http";
import { loadWorkspaceProfile } from "../../state/onboarding";
import { isDemoMode } from "../../state/settings";
import { trackUsage } from "../../state/usage";
import { Card } from "../../ui/card";
import { StatusBadge } from "../../ui/status-badge";
import { PeriodSelector } from "../../ui/period-selector";
import { loadPeriodSelection, previousPeriod, type PeriodSelection } from "../../state/period";
import { toast } from "../../ui/toast";
import { FirstRunChecklist } from "../../ui/first-run-checklist";

function kpiCard(props: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
}) {
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-xs text-slate-300">{props.label}</div>
          <div className="mt-1 text-xl font-semibold">{props.value}</div>
          {props.sub ? <div className="mt-1 text-xs text-slate-400">{props.sub}</div> : null}
        </div>
        <div className="rounded-lg bg-slate-950/40 p-2 text-slate-200">{props.icon}</div>
      </div>
    </Card>
  );
}

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
    <div className="space-y-6">
      <FirstRunChecklist />
      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <div className="text-2xl font-semibold">Финансовая аналитика продавца</div>
            {demo ? (
              <StatusBadge tone="info">
                <Sparkles className="mr-1 inline h-3 w-3" />
                Демо
              </StatusBadge>
            ) : null}
          </div>
          <div className="text-sm text-slate-300">Периодная аналитика с прозрачностью, полнотой и предупреждениями.</div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            className="rounded-lg bg-sky-500/90 px-3 py-2 text-sm font-medium text-white hover:bg-sky-400"
            to="/app/reports/upload"
            onClick={() => trackUsage("cta_upload")}
          >
            Загрузить отчёт
          </Link>
          <Link
            className="rounded-lg bg-slate-800 px-3 py-2 text-sm text-slate-100 hover:bg-slate-700"
            to="/app/ai/recommendations"
          >
            Рекомендации ИИ
          </Link>
          <button
            className="rounded-lg bg-emerald-500/90 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-400"
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

      <Card className="p-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="text-sm font-semibold">Что требует внимания сегодня</div>
            <div className="mt-1 text-xs text-slate-400">
              Ежедневное рабочее место продавца: риски, утечки прибыли, задачи и доверие к данным.
            </div>
          </div>
          <Link to="/app/today" className="text-sm text-sky-300 hover:underline">
            Открыть брифинг “Сегодня” →
          </Link>
        </div>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
          <Card className="p-4">
            <div className="text-xs text-slate-300">Критические проблемы</div>
            <div className="mt-2 text-sm text-slate-200">
              {(todaysFocus.data?.dangerous ?? []).slice(0, 3).join(" · ") || "Нет критичных флагов."}
            </div>
          </Card>
          <Card className="p-4">
            <div className="text-xs text-slate-300">Утечки прибыли</div>
            <div className="mt-2 text-sm text-slate-200">
              Проверьте маржу и затраты по SKU в экономике.
            </div>
            <Link to="/app/finance/reconciliation" className="mt-2 inline-block text-xs text-sky-300 hover:underline">
              Сверка выплат →
            </Link>
          </Card>
          <Card className="p-4">
            <div className="text-xs text-slate-300">Доверие к марже</div>
            <div className="mt-2 text-sm text-slate-200">
              {completeness ? `Полнота аналитики: ${completeness}%` : "Полнота неизвестна"}
              {(aiOps.data as any)?.degraded_intelligence_mode ? " · ИИ осторожен" : ""}
            </div>
            <Link to="/app/finance/costs" className="mt-2 inline-block text-xs text-sky-300 hover:underline">
              Покрытие затрат →
            </Link>
          </Card>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
        {kpiCard({
          icon: <Database className="h-4 w-4" />,
          label: "Продажи (выбранный период)",
          value: kpiSummary.isLoading ? "…" : (kpiSummary.data?.kpis.total_revenue ?? "0"),
          sub: (
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
          ),
        })}
        {kpiCard({
          icon: <Server className="h-4 w-4" />,
          label: "Обработка данных",
          value: queue.isLoading ? "…" : queued,
          sub: <span>Задач в очереди/обработке</span>,
        })}
        {kpiCard({
          icon: <Bot className="h-4 w-4" />,
          label: "Рекомендации ИИ",
          value: recommendations.isLoading ? "…" : recCount,
          sub: (
            <span>
              {(aiOps.data as Record<string, unknown>)?.degraded_intelligence_mode
                ? "Осторожный режим"
                : "Обычный режим"}
            </span>
          ),
        })}
        {kpiCard({
          icon: <AlertTriangle className="h-4 w-4" />,
          label: "Обновление аналитики",
          value: runtime.isLoading ? "…" : (rebuild.running ?? 0) + (rebuild.pending_dispatch ?? 0),
          sub: <span>Пересборки активны или в очереди</span>,
        })}
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <Card className="p-5 md:col-span-2">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold">Тренд продаж и прибыли (по дням)</div>
            <StatusBadge tone={stale ? "warn" : "info"}>
              <LineChartIcon className="mr-1 inline h-3 w-3" />
              {stale ? "устарело" : "актуально"}
            </StatusBadge>
          </div>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={(kpiTrend.data?.points ?? []).map((p) => ({
                  date: p.date.slice(5),
                  revenue: Number(p.revenue),
                  profit: Number(p.net_profit),
                }))}
              >
                <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} />
                <Tooltip contentStyle={{ background: "#0b1220", border: "1px solid #1f2937" }} />
                <Line type="monotone" dataKey="revenue" stroke="#38bdf8" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="profit" stroke="#34d399" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 text-xs text-slate-400">
            Данные проанализированы за период: {start} → {end} · Последнее обновление: {freshness?.data_as_of ?? "—"}
            {completeness ? <> · Полнота аналитики: {completeness}%</> : null}
          </div>
          {integrityWarnings.length ? (
            <div className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100">
              <div className="font-semibold">Предупреждения целостности</div>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {integrityWarnings.slice(0, 4).map((w) => (
                  <li key={w.code}>{w.message}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </Card>

        <Card className="p-5">
          <div className="text-sm font-semibold">Топ SKU по продажам</div>
          <div className="mt-2 text-xs text-slate-400">
            Период: {start} → {end} · {marketplace}
          </div>
          <div className="mt-4 space-y-2">
            {(topSkus.data?.items ?? []).length === 0 ? (
              <div className="text-sm text-slate-300">Пока нет метрик по SKU.</div>
            ) : (
              (topSkus.data?.items ?? []).map((row) => (
                <div key={row.sku} className="flex items-center justify-between gap-3">
                  <div className="truncate text-sm text-slate-200">{row.sku}</div>
                  <div className="text-right text-xs text-slate-300">
                    {row.revenue}
                    <div className="text-[11px] text-slate-500">
                      {row.contribution_pct ? `Доля: ${row.contribution_pct}%` : "—"}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
          <div className="mt-4 space-y-2 text-xs text-slate-400">
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

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <Card className="p-5 md:col-span-2">
          <div className="text-sm font-semibold">Затраты и возвраты (по дням)</div>
          <div className="mt-4 h-64">
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
                <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 12 }} />
                <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} />
                <Tooltip contentStyle={{ background: "#0b1220", border: "1px solid #1f2937" }} />
                <Line type="monotone" dataKey="logistics" stroke="#fbbf24" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="ads" stroke="#a78bfa" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="returns" stroke="#fb7185" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="payout" stroke="#60a5fa" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 text-xs text-slate-400">
            Логистика · Продвижение · Возвраты · Выплаты
          </div>
        </Card>

        <Card className="p-5">
          <div className="text-sm font-semibold">Финансовая сводка</div>
          <div className="mt-2 text-xs text-slate-400">Период: {start} → {end}</div>
          <div className="mt-4 space-y-2 text-sm text-slate-200">
            <div className="flex justify-between gap-3"><span>Продажа, руб.</span><span>{financeSummary.data?.kpis.sales_revenue ?? "—"}</span></div>
            <div className="flex justify-between gap-3"><span>Возвраты, руб.</span><span>{financeSummary.data?.kpis.returns_amount ?? "—"}</span></div>
            <div className="flex justify-between gap-3"><span>Стоимость логистики, руб.</span><span>{financeSummary.data?.kpis.logistics ?? "—"}</span></div>
            <div className="flex justify-between gap-3"><span>Затраты на продвижение, руб.</span><span>{financeSummary.data?.kpis.advertisement ?? "—"}</span></div>
            <div className="flex justify-between gap-3"><span>Штрафы, руб.</span><span>{financeSummary.data?.kpis.penalties ?? "—"}</span></div>
            <div className="flex justify-between gap-3"><span>Хранение, руб.</span><span>{financeSummary.data?.kpis.storage_fee ?? "—"}</span></div>
            <div className="flex justify-between gap-3"><span>К перечислению, руб.</span><span>{financeSummary.data?.kpis.payout ?? "—"}</span></div>
            <div className="mt-2 border-t border-slate-800 pt-2 flex justify-between gap-3 font-semibold">
              <span>Валовая прибыль, руб.</span><span>{financeSummary.data?.kpis.gross_profit ?? "—"}</span>
            </div>
            <div className="flex justify-between gap-3">
              <span>Маржинальность, %</span><span>{financeSummary.data?.kpis.margin_pct ?? "—"}</span>
            </div>
            <div className="flex justify-between gap-3">
              <span>Процент возвратов</span><span>{financeSummary.data?.kpis.return_rate_pct ?? "—"}%</span>
            </div>
          </div>
          <div className="mt-3 text-xs text-slate-400">
            Некоторые показатели могут быть неполными, если не загружены нужные отчёты или себестоимость.
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <Card className="p-5">
          <div className="text-sm font-semibold">Ежедневный сценарий</div>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-slate-300">
            <li>Загрузите свежий отчёт (если есть)</li>
            <li>
              Проверьте <Link className="text-sky-300 hover:underline" to="/app/status">статус системы</Link> (очередь/пересборки)
            </li>
            <li>
              Откройте <Link className="text-sky-300 hover:underline" to="/app/ai/recommendations">входящие ИИ</Link> или{" "}
              <Link className="text-sky-300 hover:underline" to="/app/ai/today">фокус на сегодня</Link>
              {" · "}
              <Link className="text-sky-300 hover:underline" to="/app/ai/digest?type=daily">ежедневный дайджест</Link>
            </li>
            <li>Сохраните/отклоните рекомендации и оставьте обратную связь</li>
          </ol>
        </Card>
        <Card className="p-5">
          <div className="text-sm font-semibold">Доверие к данным</div>
          <p className="mt-2 text-sm text-slate-300">
            Финансовые KPI берутся из read-only аналитического слоя. Если данные устарели — проверьте пересборки и очередь;
            в режиме устаревания трактуйте выводы ИИ осторожно.
          </p>
          <Link to="/app/onboarding" className="mt-3 inline-block text-sm text-sky-300 hover:underline">
            Завершить настройку →
          </Link>
        </Card>
      </div>

      {demo ? (
        <Card className="border-sky-500/30 bg-sky-500/10 p-5">
          <div className="text-sm font-semibold text-sky-100">Демо-сценарий</div>
          <p className="mt-2 text-sm text-slate-200">
            1) Загрузка отчёта → 2) Обработка → 3) Рекомендация ИИ → 4) Объяснимость → 5) Действие и оценка полезности.
          </p>
          <Link to="/app/support" className="mt-3 inline-block text-sm text-sky-300 hover:underline">
            Отладка демо →
          </Link>
        </Card>
      ) : null}
    </div>
  );
}
