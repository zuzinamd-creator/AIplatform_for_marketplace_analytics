/** Cost composition helpers for Dashboard (Phase 9.14-B). */

export type FinanceTrendCostPoint = {
  date: string;
  logistics?: string | number | null;
  advertisement?: string | number | null;
  returns_amount?: string | number | null;
  payout?: string | number | null;
  commission?: string | number | null;
  storage_fee?: string | number | null;
  penalties?: string | number | null;
  deductions?: string | number | null;
  acquiring?: string | number | null;
  other?: string | number | null;
};

export type CostStructureChartRow = {
  date: string;
  commission: number;
  logistics: number;
  advertisement: number;
  returns: number;
  storage: number;
  penalties: number;
  deductions: number;
  acquiring: number;
  other: number;
};

export type CostFillKey =
  | "commission"
  | "logistics"
  | "ads"
  | "returns"
  | "storage"
  | "penalties"
  | "deductions"
  | "acquiring"
  | "other"
  | "otherCosts"
  | "costTotal";

export type CostCategoryKey =
  | "commission"
  | "logistics"
  | "advertisement"
  | "returns"
  | "storage"
  | "penalties"
  | "deductions"
  | "acquiring"
  | "other";

export type CostCategoryDef = {
  key: CostCategoryKey;
  /** Short chart/legend label */
  name: string;
  /** Plain-seller one-liner */
  hint: string;
  fillKey: CostFillKey;
  /** finance_summary field (returns uses returns_amount) */
  summaryField:
    | "commission"
    | "logistics"
    | "advertisement"
    | "returns_amount"
    | "storage_fee"
    | "penalties"
    | "deductions"
    | "acquiring"
    | "other";
};

/** Seller-facing category dictionary (includes «Удержания»). */
export const COST_CATEGORIES: readonly CostCategoryDef[] = [
  {
    key: "commission",
    name: "Комиссия WB",
    hint: "Комиссия маркетплейса за продажи",
    fillKey: "commission",
    summaryField: "commission",
  },
  {
    key: "logistics",
    name: "Логистика",
    hint: "Доставка и обработка заказов",
    fillKey: "logistics",
    summaryField: "logistics",
  },
  {
    key: "advertisement",
    name: "Продвижение",
    hint: "Реклама и продвижение на площадке",
    fillKey: "ads",
    summaryField: "advertisement",
  },
  {
    key: "returns",
    name: "Возвраты",
    hint: "Сумма возвратов покупателей",
    fillKey: "returns",
    summaryField: "returns_amount",
  },
  {
    key: "storage",
    name: "Хранение",
    hint: "Плата за хранение на складе WB",
    fillKey: "storage",
    summaryField: "storage_fee",
  },
  {
    key: "penalties",
    name: "Штрафы",
    hint: "Штрафы и пени от маркетплейса",
    fillKey: "penalties",
    summaryField: "penalties",
  },
  {
    key: "deductions",
    name: "Удержания",
    hint: "Прочие списания WB (в т.ч. услуги и подписки, если они в удержаниях отчёта)",
    fillKey: "deductions",
    summaryField: "deductions",
  },
  {
    key: "acquiring",
    name: "Эквайринг",
    hint: "Комиссия за приём оплаты",
    fillKey: "acquiring",
    summaryField: "acquiring",
  },
  {
    key: "other",
    name: "Прочее",
    hint: "Другие операции расходов",
    fillKey: "other",
    summaryField: "other",
  },
] as const;

export type PeriodCostSlice = {
  key: CostCategoryKey;
  name: string;
  hint: string;
  fillKey: CostFillKey;
  amount: number;
  sharePct: number;
};

export type PeriodCostComposition = {
  total: number;
  slices: PeriodCostSlice[];
};

/** Room for Russian category labels + end % labels; grows with slice count. */
export function costStructureChartHeight(sliceCount: number): number {
  return Math.max(256, sliceCount * 40 + 24);
}

function num(value: string | number | null | undefined): number {
  if (value == null || value === "") return 0;
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

export function mapFinanceTrendToCostStructure(
  points: FinanceTrendCostPoint[] | null | undefined,
): CostStructureChartRow[] {
  return (points ?? []).map((p) => ({
    date: p.date.length >= 10 ? p.date.slice(5) : p.date,
    commission: num(p.commission),
    logistics: num(p.logistics),
    advertisement: num(p.advertisement),
    returns: num(p.returns_amount),
    storage: num(p.storage_fee),
    penalties: num(p.penalties),
    deductions: num(p.deductions),
    acquiring: num(p.acquiring),
    other: num(p.other),
  }));
}

/** Period composition from finance_summary (primary view). Sorted by amount desc; zeros omitted. */
export function buildPeriodCostComposition(
  kpis: Record<string, string | number | null | undefined> | null | undefined,
): PeriodCostComposition {
  const amounts = COST_CATEGORIES.map((cat) => ({
    cat,
    amount: num(kpis?.[cat.summaryField]),
  }));
  const total = amounts.reduce((s, row) => s + row.amount, 0);
  const slices: PeriodCostSlice[] = amounts
    .filter((row) => row.amount > 0)
    .sort((a, b) => b.amount - a.amount)
    .map((row) => ({
      key: row.cat.key,
      name: row.cat.name,
      hint: row.cat.hint,
      fillKey: row.cat.fillKey,
      amount: row.amount,
      sharePct: total > 0 ? (row.amount / total) * 100 : 0,
    }));
  return { total, slices };
}

export const COST_STRUCTURE_STACK_ID = "cost-structure";

/** Categories included in daily total costs (returns excluded by product rule). */
export const DAILY_TOTAL_COST_KEYS = [
  "commission",
  "logistics",
  "advertisement",
  "storage",
  "penalties",
  "deductions",
  "acquiring",
  "other",
] as const satisfies readonly Exclude<CostCategoryKey, "returns">[];

export type DailyTotalCostRow = {
  date: string;
  total_costs: number;
  commission: number;
  logistics: number;
  advertisement: number;
  storage: number;
  penalties: number;
  deductions: number;
  acquiring: number;
  other: number;
};

/** Daily total costs = sum of expense categories excluding returns. */
export function buildDailyTotalCostsChart(
  points: FinanceTrendCostPoint[] | null | undefined,
): { rows: DailyTotalCostRow[]; hasData: boolean } {
  const detailed = mapFinanceTrendToCostStructure(points);
  const rows: DailyTotalCostRow[] = detailed.map((row) => {
    const commission = row.commission;
    const logistics = row.logistics;
    const advertisement = row.advertisement;
    const storage = row.storage;
    const penalties = row.penalties;
    const deductions = row.deductions;
    const acquiring = row.acquiring;
    const other = row.other;
    const total_costs =
      commission + logistics + advertisement + storage + penalties + deductions + acquiring + other;
    return {
      date: row.date,
      total_costs,
      commission,
      logistics,
      advertisement,
      storage,
      penalties,
      deductions,
      acquiring,
      other,
    };
  });
  const hasData = rows.some((r) => r.total_costs > 0);
  return { rows, hasData };
}

/** @deprecated Prefer buildDailyTotalCostsChart (Phase 9.15-B). Kept for compat tests. */
export const DAILY_TOP_N = 3;

export type DailyCostSeriesDef = {
  dataKey: string;
  name: string;
  fillKey: CostFillKey;
};

export type DailyCostChartRow = {
  date: string;
  [key: string]: string | number;
};

/** @deprecated Prefer buildDailyTotalCostsChart. */
export function buildDailyCostChart(
  points: FinanceTrendCostPoint[] | null | undefined,
  topN: number = DAILY_TOP_N,
): { rows: DailyCostChartRow[]; series: DailyCostSeriesDef[] } {
  const detailed = mapFinanceTrendToCostStructure(points);
  const totals: Record<CostCategoryKey, number> = {
    commission: 0,
    logistics: 0,
    advertisement: 0,
    returns: 0,
    storage: 0,
    penalties: 0,
    deductions: 0,
    acquiring: 0,
    other: 0,
  };
  for (const row of detailed) {
    for (const cat of COST_CATEGORIES) {
      totals[cat.key] += row[cat.key];
    }
  }
  const ranked = [...COST_CATEGORIES]
    .map((cat) => ({ cat, total: totals[cat.key] }))
    .filter((r) => r.total > 0)
    .sort((a, b) => b.total - a.total);

  const top = ranked.slice(0, topN).map((r) => r.cat);
  const rest = ranked.slice(topN).map((r) => r.cat);
  const series: DailyCostSeriesDef[] = top.map((cat) => ({
    dataKey: cat.key,
    name: cat.name,
    fillKey: cat.fillKey,
  }));
  if (rest.length > 0) {
    series.push({ dataKey: "rest", name: "Остальное", fillKey: "otherCosts" });
  }

  const rows: DailyCostChartRow[] = detailed.map((row) => {
    const out: DailyCostChartRow = { date: row.date };
    for (const cat of top) {
      out[cat.key] = row[cat.key];
    }
    if (rest.length > 0) {
      out.rest = rest.reduce((s, cat) => s + row[cat.key], 0);
    }
    return out;
  });

  return { rows, series };
}

/** @deprecated naming — prefer COST_CATEGORIES / buildPeriodCostComposition */
export type CostStructureSeriesDef = {
  dataKey: CostCategoryKey;
  name: string;
  fillKey: CostFillKey;
};

export const COST_STRUCTURE_CORE_SERIES: readonly CostStructureSeriesDef[] = COST_CATEGORIES.filter(
  (c) => c.key !== "other",
).map((c) => ({ dataKey: c.key, name: c.name, fillKey: c.fillKey }));

export function hasNonZeroOther(rows: CostStructureChartRow[]): boolean {
  return rows.some((r) => r.other > 0);
}

export function costStructureSeriesFor(rows: CostStructureChartRow[]): CostStructureSeriesDef[] {
  const core = [...COST_STRUCTURE_CORE_SERIES];
  return hasNonZeroOther(rows)
    ? [...core, { dataKey: "other", name: "Прочее", fillKey: "other" }]
    : core;
}

export const COST_STRUCTURE_SERIES = COST_STRUCTURE_CORE_SERIES;
