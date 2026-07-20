import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { CHART } from "../../ui/chart-theme";
import { formatCompactRub, formatPct, formatRub } from "../../utils/format";
import { costDynamicsInsight, costStructureInsight } from "./chart-insights";
import {
  buildDailyTotalCostsChart,
  buildPeriodCostComposition,
  costStructureChartHeight,
  type DailyTotalCostRow,
  type FinanceTrendCostPoint,
} from "./cost-structure-chart";

export type CostStructurePanelProps = {
  periodStart: string;
  periodEnd: string;
  financeKpis: Record<string, string | number | null | undefined> | null | undefined;
  trendPoints: FinanceTrendCostPoint[] | null | undefined;
};

const BREAKDOWN_TOOLTIP_FIELDS: Array<{ key: keyof DailyTotalCostRow; name: string }> = [
  { key: "commission", name: "Комиссия WB" },
  { key: "logistics", name: "Логистика" },
  { key: "advertisement", name: "Продвижение" },
  { key: "storage", name: "Хранение" },
  { key: "penalties", name: "Штрафы" },
  { key: "deductions", name: "Удержания" },
  { key: "acquiring", name: "Эквайринг" },
  { key: "other", name: "Прочее" },
];

const MAX_DAILY_LABELED_POINTS = 14;

function formatShareLabel(value: unknown): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  return `${Math.round(n)}%`;
}

function DailyTotalTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ payload?: DailyTotalCostRow; value?: number | string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const row = payload[0]?.payload;
  if (!row) return null;
  return (
    <div style={CHART.tooltip}>
      <div className="mb-1 font-medium">{label}</div>
      <div>{formatRub(row.total_costs)} · Всего затрат</div>
      <ul className="mt-2 space-y-0.5 text-[11px]">
        {BREAKDOWN_TOOLTIP_FIELDS.filter((f) => Number(row[f.key]) > 0).map((f) => (
          <li key={f.key}>
            {f.name}: {formatRub(row[f.key])}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function CostStructurePanel({
  periodStart,
  periodEnd,
  financeKpis,
  trendPoints,
}: CostStructurePanelProps) {
  const composition = buildPeriodCostComposition(financeKpis);
  const daily = buildDailyTotalCostsChart(trendPoints);
  const structureInsight = costStructureInsight(composition);
  const dynamicsInsight = costDynamicsInsight(daily.rows);
  const structureRows = composition.slices.map((s) => ({
    name: s.name,
    amount: s.amount,
    sharePct: s.sharePct,
    fillKey: s.fillKey,
  }));
  const structureHeight = costStructureChartHeight(structureRows.length);
  const showDailyLabels = daily.rows.length > 0 && daily.rows.length <= MAX_DAILY_LABELED_POINTS;

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
            <div
              className="mt-4 w-full"
              style={{ height: structureHeight }}
              data-testid="cost-structure-chart"
            >
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  layout="vertical"
                  data={structureRows}
                  margin={{ top: 4, right: 48, left: 4, bottom: 4 }}
                >
                  <XAxis type="number" tick={CHART.axis} hide={false} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={CHART.costCategoryAxisWidth}
                    tick={CHART.axis}
                    interval={0}
                  />
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
                    <LabelList
                      dataKey="sharePct"
                      position="right"
                      formatter={formatShareLabel}
                      style={CHART.barLabel}
                    />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <ul className="mt-4 space-y-2" data-testid="cost-composition-legend">
              {composition.slices.map((s) => (
                <li
                  key={s.key}
                  className="flex items-start gap-2 text-sm"
                  data-testid={`cost-legend-${s.key}`}
                >
                  <span
                    className="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-sm"
                    style={{ background: CHART.series[s.fillKey] }}
                    aria-hidden
                  />
                  <span className="min-w-0 flex-1">
                    <span className="font-medium text-ink">
                      {s.name}: {formatRub(s.amount)} ({Math.round(s.sharePct)}%)
                    </span>
                    <span className="mt-0.5 block text-xs text-ink-muted">{s.hint}</span>
                  </span>
                </li>
              ))}
            </ul>
            <div className="mt-2 text-xs text-ink-muted" data-testid="cost-share-note">
              % — доля от общей суммы расходов за период
            </div>
            {structureInsight ? (
              <div className="mt-3 text-xs text-ink-muted" data-testid="cost-structure-insight">
                {structureInsight}
              </div>
            ) : null}
          </>
        )}
      </div>

      <div>
        <div className="text-sm font-semibold text-ink">Общие затраты по дням</div>
        <div className="mt-1 text-xs text-ink-muted">
          Сумма расходов WB без возвратов (комиссия + логистика + продвижение + хранение + штрафы +
          удержания + эквайринг + прочее). Разбивка дня — во всплывающей подсказке.
        </div>
        {!daily.hasData ? (
          <div className="mt-4 text-sm text-ink-muted">Нет дневных данных по расходам.</div>
        ) : (
          <>
            <div className="chart-panel mt-4" data-testid="daily-costs-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={daily.rows} margin={{ top: 18, right: 8, left: 0, bottom: 0 }}>
                  <XAxis dataKey="date" tick={CHART.axis} />
                  <YAxis tick={CHART.axis} width={48} />
                  <Tooltip content={<DailyTotalTooltip />} />
                  <Bar
                    dataKey="total_costs"
                    name="Затраты"
                    fill={CHART.series.costTotal}
                    radius={[2, 2, 0, 0]}
                  >
                    {showDailyLabels ? (
                      <LabelList
                        dataKey="total_costs"
                        position="top"
                        formatter={(v: unknown) => formatCompactRub(v)}
                        style={CHART.barLabel}
                      />
                    ) : null}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-1 text-xs text-ink-muted" data-testid="daily-costs-share-note">
              Подписи на столбцах при ≤{MAX_DAILY_LABELED_POINTS} днях; иначе — только оси и tooltip.
            </div>

            {dynamicsInsight ? (
              <div className="mt-3 text-xs text-ink-muted" data-testid="cost-dynamics-insight">
                {dynamicsInsight}
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
