import { Suspense, lazy } from "react";
import {
  Bar,
  BarChart,
  LabelList,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { CHART } from "../../ui/chart-theme";
import { chartRubTooltip, formatCompactRub } from "../../utils/format";
import type { ProfitTrustContext } from "../../state/profit-trust";
import { chartTrustNumeric } from "../../state/profit-trust";

/** Hide on-bar labels when the period has too many days (mobile / dense charts). */
const MAX_LABELED_CHART_POINTS = 14;

function chartBarLabel(value: unknown): string {
  if (value == null || value === "") return "";
  return formatCompactRub(value);
}

export type RevenueTrendPoint = {
  date: string;
  revenue?: string | number | null;
  net_profit?: string | number | null;
  seller_profit?: string | number | null;
};

export type RevenueTrendChartProps = {
  points: RevenueTrendPoint[] | null | undefined;
  trustCtx: ProfitTrustContext;
};

/** Isolated so Vite can code-split Recharts off the dashboard critical path. */
export function RevenueTrendChart({ points, trustCtx }: RevenueTrendChartProps) {
  const rows = (points ?? []).map((p) => ({
    date: p.date.slice(5),
    revenue: Number(p.revenue),
    profit: chartTrustNumeric(p.seller_profit ?? p.net_profit, trustCtx.trust),
  }));

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={rows} margin={{ top: 18, right: 8, left: 0, bottom: 0 }}>
        <XAxis dataKey="date" tick={CHART.axis} />
        <YAxis tick={CHART.axis} />
        <Tooltip
          contentStyle={CHART.tooltip}
          formatter={(value, name) => chartRubTooltip(value, String(name))}
        />
        <Legend />
        <Bar dataKey="revenue" name="Выручка" fill={CHART.series.revenue} radius={[2, 2, 0, 0]}>
          {rows.length <= MAX_LABELED_CHART_POINTS ? (
            <LabelList
              dataKey="revenue"
              position="top"
              formatter={chartBarLabel}
              style={{ fill: "#64748b", fontSize: 10 }}
            />
          ) : null}
        </Bar>
        {trustCtx.canShowProfit ? (
          <Bar
            dataKey="profit"
            name="Прибыль"
            fill={CHART.series.profit}
            radius={[2, 2, 0, 0]}
            fillOpacity={trustCtx.trust === "partial" ? 0.55 : 1}
          >
            {rows.length <= MAX_LABELED_CHART_POINTS ? (
              <LabelList
                dataKey="profit"
                position="top"
                formatter={chartBarLabel}
                style={{ fill: "#64748b", fontSize: 10 }}
              />
            ) : null}
          </Bar>
        ) : null}
      </BarChart>
    </ResponsiveContainer>
  );
}

const LazyRevenueTrendChart = lazy(async () => ({
  default: RevenueTrendChart,
}));

const LazyCostStructurePanel = lazy(async () => {
  const mod = await import("./CostStructurePanel");
  return { default: mod.CostStructurePanel };
});

export function DeferredRevenueTrendChart(props: RevenueTrendChartProps) {
  return (
    <Suspense fallback={<div className="flex h-full items-center justify-center text-xs text-ink-muted">Загрузка графика…</div>}>
      <LazyRevenueTrendChart {...props} />
    </Suspense>
  );
}

export type DeferredCostStructurePanelProps = {
  periodStart: string;
  periodEnd: string;
  financeKpis: Record<string, string | number | null | undefined> | null | undefined;
  trendPoints: import("./cost-structure-chart").FinanceTrendCostPoint[] | null | undefined;
};

export function DeferredCostStructurePanel(props: DeferredCostStructurePanelProps) {
  return (
    <Suspense fallback={<div className="py-8 text-center text-xs text-ink-muted">Загрузка структуры затрат…</div>}>
      <LazyCostStructurePanel {...props} />
    </Suspense>
  );
}
