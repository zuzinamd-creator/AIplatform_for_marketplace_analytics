import {
  Bar,
  BarChart,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { CHART } from "../../ui/chart-theme";
import { formatPct, formatRub, chartRubTooltip } from "../../utils/format";
import {
  buildDailyCostChart,
  buildPeriodCostComposition,
  COST_STRUCTURE_STACK_ID,
  type FinanceTrendCostPoint,
} from "./cost-structure-chart";

export type CostStructurePanelProps = {
  periodStart: string;
  periodEnd: string;
  financeKpis: Record<string, string | number | null | undefined> | null | undefined;
  trendPoints: FinanceTrendCostPoint[] | null | undefined;
};

export function CostStructurePanel({
  periodStart,
  periodEnd,
  financeKpis,
  trendPoints,
}: CostStructurePanelProps) {
  const composition = buildPeriodCostComposition(financeKpis);
  const daily = buildDailyCostChart(trendPoints);

  return (
    <div className="space-y-6">
      <div>
        <div className="text-sm font-semibold text-ink">Структура расходов за период</div>
        <div className="mt-1 text-xs text-ink-muted">
          {periodStart} → {periodEnd}
          {composition.total > 0 ? ` · Всего расходов: ${formatRub(composition.total)}` : null}
        </div>

        {composition.slices.length === 0 ? (
          <div className="mt-4 text-sm text-ink-muted">Нет данных по расходам за период.</div>
        ) : (
          <>
            <div className="chart-panel mt-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  layout="vertical"
                  data={composition.slices.map((s) => ({
                    name: s.name,
                    amount: s.amount,
                    sharePct: s.sharePct,
                    fillKey: s.fillKey,
                  }))}
                  margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
                >
                  <XAxis type="number" tick={CHART.axis} />
                  <YAxis type="category" dataKey="name" width={110} tick={CHART.axis} />
                  <Tooltip
                    contentStyle={CHART.tooltip}
                    formatter={(value, _name, item) => {
                      const share = item?.payload?.sharePct;
                      const label =
                        share != null ? `${formatRub(value)} (${formatPct(share)})` : formatRub(value);
                      return [label, "Сумма"];
                    }}
                  />
                  <Bar dataKey="amount" name="Сумма" radius={[0, 4, 4, 0]}>
                    {composition.slices.map((s) => (
                      <Cell key={s.key} fill={CHART.series[s.fillKey]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <ul className="mt-4 space-y-2" data-testid="cost-composition-legend">
              {composition.slices.map((s) => (
                <li key={s.key} className="flex items-start gap-2 text-sm">
                  <span
                    className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-sm"
                    style={{ background: CHART.series[s.fillKey] }}
                    aria-hidden
                  />
                  <span className="min-w-0 flex-1">
                    <span className="font-medium text-ink-secondary">
                      {s.name}: {formatRub(s.amount)} ({Math.round(s.sharePct)}%)
                    </span>
                    <span className="mt-0.5 block text-xs text-ink-muted">{s.hint}</span>
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>

      <div>
        <div className="text-sm font-semibold text-ink">Динамика по дням</div>
        <div className="mt-1 text-xs text-ink-muted">
          Топ категорий расходов; остальное объединено
        </div>
        {daily.series.length === 0 ? (
          <div className="mt-4 text-sm text-ink-muted">Нет дневных данных по расходам.</div>
        ) : (
          <div className="chart-panel mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={daily.rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <XAxis dataKey="date" tick={CHART.axis} />
                <YAxis tick={CHART.axis} />
                <Tooltip
                  contentStyle={CHART.tooltip}
                  formatter={(value, name) => chartRubTooltip(value, String(name))}
                />
                <Legend />
                {daily.series.map((series, index) => (
                  <Bar
                    key={series.dataKey}
                    dataKey={series.dataKey}
                    name={series.name}
                    stackId={COST_STRUCTURE_STACK_ID}
                    fill={CHART.series[series.fillKey]}
                    radius={index === daily.series.length - 1 ? [2, 2, 0, 0] : undefined}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
