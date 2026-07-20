import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Bot, LineChart as LineChartIcon, Server, Sparkles } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useEffect } from "react";

import { useAuth } from "../../state/auth";
import { api } from "../../state/http";
import { loadWorkspaceProfile } from "../../state/onboarding";
import { isDemoMode } from "../../state/settings";
import { trackUsage } from "../../state/usage";
import { isPlatformAdmin } from "../../state/userRoles";
import { useProfitTrust } from "../../state/profit-trust";
import { formatMetric, formatPct } from "../../utils/format";
import { Card } from "../../ui/card";
import { CollapsibleSection } from "../../ui/collapsible-section";
import { KpiCard } from "../../ui/kpi-card";
import { StatusBadge } from "../../ui/status-badge";
import { WarnCallout } from "../../ui/warn-callout";
import { PeriodSelector } from "../../ui/period-selector";
import { usePagePeriod } from "../../state/use-page-period";
import { FirstRunChecklist } from "../../ui/first-run-checklist";
import { FinancialSummaryCard } from "./FinancialSummaryCard";
import { TopSkusCard } from "./TopSkusCard";
import { DeferredCostStructurePanel, DeferredRevenueTrendChart } from "./DeferredCharts";
import { revenueProfitInsight } from "./chart-insights";
import { PrimaryAnswer } from "./PrimaryAnswer";
import { ActionStrip } from "./ActionStrip";
import { buildActionCardsFromSummary, COST_SECTION_ANCHOR } from "./action-strip";
import { scrollToHashTarget } from "./hash-scroll";

export function DashboardPage() {
  const location = useLocation();

  useEffect(() => {
    trackUsage("view_dashboard");
  }, []);

  // Deep-link / cross-route hash: RR does not scroll to #dashboard-cost-structure by itself.
  useEffect(() => {
    if (location.hash !== `#${COST_SECTION_ANCHOR}`) return;
    const timer = window.setTimeout(() => {
      scrollToHashTarget(location.hash, "smooth");
    }, 50);
    return () => window.clearTimeout(timer);
  }, [location.hash, location.key]);

  const { user } = useAuth();
  const admin = isPlatformAdmin(user);
  const demo = isDemoMode();
  const workspace = loadWorkspaceProfile();
  const marketplace = workspace.marketplace === "unknown" ? "wildberries" : workspace.marketplace;
  const { periodSel, setPeriodSel } = usePagePeriod();
  const start = periodSel.range.start;
  const end = periodSel.range.end;

  const summary = useQuery({
    queryKey: ["dashboard", "summary", marketplace, start, end],
    queryFn: () =>
      api.dashboard.summary({
        marketplace,
        start,
        end,
      }),
  });

  const data = summary.data;
  const isLoading = summary.isLoading;

  const statusCounts = data?.queue.status_counts ?? {};
  const queued = Object.values(statusCounts).reduce((a, b) => a + b, 0);
  // Slim summary returns items=[] with page.total (9.18-B); fall back to items.length for tests/legacy.
  const recCount =
    data?.recommendations.page?.total ?? data?.recommendations.items?.length ?? 0;
  const rebuild = (data?.runtime.rebuild ?? {}) as Record<string, number>;
  const freshness = data?.revenue_summary.freshness;
  const stale = freshness?.stale_data_warning ?? false;
  const integrityWarnings = data?.revenue_summary.integrity?.warnings ?? [];
  const completeness = data?.revenue_summary.integrity?.financial_completeness_score ?? null;
  const trustCtx = useProfitTrust(data?.revenue_summary.integrity, data?.cost_coverage ?? null);

  const actionCards = buildActionCardsFromSummary({
    trustCtx,
    dangerous: data?.todays_focus.dangerous ?? [],
    financeKpis: data?.finance_summary.kpis ?? null,
    topSkus: data?.top_skus.items ?? null,
    aiRecommendationCount: recCount,
  });
  const salesInsight = revenueProfitInsight(
    data?.revenue_trend_daily.points,
    trustCtx.canShowProfit,
    data?.finance_trend_daily.points,
  );

  return (
    <div className="page-shell">
      <FirstRunChecklist />
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
      </div>

      <div className="space-y-6" data-testid="dashboard-above-fold">
        <PeriodSelector value={periodSel} onChange={setPeriodSel} />

        <PrimaryAnswer
          revenue={data?.revenue_summary.kpis.total_revenue}
          profit={data?.revenue_summary.kpis.total_profit}
          trustCtx={trustCtx}
          isLoading={isLoading}
        />

        <ActionStrip cards={actionCards} isLoading={isLoading} />

        <TopSkusCard
          marketplace={marketplace}
          start={start}
          end={end}
          summaryTopSkus={data?.top_skus}
          trustCtx={trustCtx}
          coverageMin={data?.coverage.available_min_date}
          coverageMax={data?.coverage.available_max_date}
          missingPeriodsCount={(data?.coverage.missing_periods ?? []).length}
        />
      </div>

      {salesInsight ? (
        <div className="text-sm text-ink-secondary" data-testid="dashboard-insight-line">
          {salesInsight}
        </div>
      ) : null}

      <Card className="p-6">
        <div className="flex items-center justify-between gap-3">
          <div className="text-sm font-semibold text-ink">Выручка и прибыль по дням</div>
          <StatusBadge tone={stale ? "warn" : "info"}>
            <LineChartIcon className="mr-1 inline h-3 w-3" />
            {stale ? "устарело" : "актуально"}
          </StatusBadge>
        </div>
        <div className="chart-panel mt-5">
          <DeferredRevenueTrendChart
            points={data?.revenue_trend_daily.points}
            trustCtx={trustCtx}
          />
        </div>
        <div className="mt-3 text-xs text-ink-muted">
          Период: {start} → {end} · Обновлено: {freshness?.data_as_of ?? "—"}
          {completeness ? <> · Полнота данных: {formatPct(completeness)}</> : null}
        </div>
        {integrityWarnings.length ? (
          <WarnCallout title="Предупреждения целостности" className="mt-4">
            <ul className="list-disc space-y-1 pl-5 text-xs">
              {integrityWarnings.slice(0, 4).map((w) => (
                <li key={w.code}>{w.message}</li>
              ))}
            </ul>
          </WarnCallout>
        ) : null}
      </Card>

      <FinancialSummaryCard
        periodStart={start}
        periodEnd={end}
        totalRevenue={data?.revenue_summary.kpis.total_revenue}
        financeKpis={data?.finance_summary.kpis}
        trustCtx={trustCtx}
      />

      <Card className="p-6" id={COST_SECTION_ANCHOR}>
        <DeferredCostStructurePanel
          periodStart={start}
          periodEnd={end}
          financeKpis={data?.finance_summary.kpis}
          trendPoints={data?.finance_trend_daily.points}
        />
      </Card>

      <div className="flex flex-wrap gap-3" data-testid="dashboard-secondary-links">
        <Link className="link-muted text-sm" to="/app/analytics/weekly">
          Сравнение периодов
        </Link>
        <Link className="link-muted text-sm" to="/app/economics">
          Экономика SKU
        </Link>
        <Link className="link-muted text-sm" to="/app/ai/recommendations">
          ИИ-помощник
        </Link>
      </div>

      {admin ? (
        <CollapsibleSection
          title="Система"
          subtitle="Очередь, рекомендации ИИ и пересборки аналитики."
          className="disclosure-panel-muted"
          data-testid="dashboard-admin-system"
        >
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3" data-testid="dashboard-admin-kpis">
            <KpiCard
              icon={<Server className="h-4 w-4" />}
              label="Обработка данных"
              value={isLoading ? "…" : formatMetric(queued)}
              sub={<span>Задач в очереди/обработке</span>}
            />
            <KpiCard
              icon={<Bot className="h-4 w-4" />}
              label="Рекомендации ИИ"
              value={isLoading ? "…" : recCount}
              sub={
                <span>
                  {(data?.ai_ops as Record<string, unknown>)?.degraded_intelligence_mode
                    ? "Осторожный режим"
                    : "Обычный режим"}
                </span>
              }
            />
            <KpiCard
              icon={<AlertTriangle className="h-4 w-4" />}
              label="Обновление аналитики"
              value={isLoading ? "…" : (rebuild.running ?? 0) + (rebuild.pending_dispatch ?? 0)}
              sub={<span>Пересборки активны или в очереди</span>}
            />
          </div>
        </CollapsibleSection>
      ) : null}

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
