/** Map finance_trend_daily points → stacked cost-structure chart rows (Phase 9.12-B3). */

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

export type CostStructureSeriesDef = {
  dataKey: keyof Omit<CostStructureChartRow, "date">;
  name: string;
  fillKey: "commission" | "logistics" | "ads" | "returns" | "storage" | "penalties" | "deductions" | "acquiring" | "other";
};

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

export const COST_STRUCTURE_STACK_ID = "cost-structure";

/** Core stack — always shown. */
export const COST_STRUCTURE_CORE_SERIES: readonly CostStructureSeriesDef[] = [
  { dataKey: "commission", name: "Комиссия", fillKey: "commission" },
  { dataKey: "logistics", name: "Логистика", fillKey: "logistics" },
  { dataKey: "advertisement", name: "Продвижение", fillKey: "ads" },
  { dataKey: "returns", name: "Возвраты", fillKey: "returns" },
  { dataKey: "storage", name: "Хранение", fillKey: "storage" },
  { dataKey: "penalties", name: "Штрафы", fillKey: "penalties" },
  { dataKey: "deductions", name: "Удержания", fillKey: "deductions" },
  { dataKey: "acquiring", name: "Эквайринг", fillKey: "acquiring" },
] as const;

const OTHER_SERIES: CostStructureSeriesDef = {
  dataKey: "other",
  name: "Прочее",
  fillKey: "other",
};

/** True when any day has non-zero ledger `other`. */
export function hasNonZeroOther(rows: CostStructureChartRow[]): boolean {
  return rows.some((r) => r.other > 0);
}

/** Legend / footer / bars — includes optional «Прочее» only when needed. */
export function costStructureSeriesFor(rows: CostStructureChartRow[]): CostStructureSeriesDef[] {
  return hasNonZeroOther(rows) ? [...COST_STRUCTURE_CORE_SERIES, OTHER_SERIES] : [...COST_STRUCTURE_CORE_SERIES];
}

/** @deprecated use costStructureSeriesFor — kept for tests naming clarity */
export const COST_STRUCTURE_SERIES = COST_STRUCTURE_CORE_SERIES;
