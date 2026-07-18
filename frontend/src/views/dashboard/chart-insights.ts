/** Deterministic chart insights — FACT + DRIVER + ATTENTION (Phase 9.16-C). No AI. */

import type { PeriodCostComposition } from "./cost-structure-chart";
import type { DailyTotalCostRow, FinanceTrendCostPoint } from "./cost-structure-chart";

export type RevenueTrendInsightPoint = {
  date: string;
  revenue?: string | number | null;
  net_profit?: string | number | null;
  seller_profit?: string | number | null;
};

export type TopSkuInsightItem = {
  sku: string;
  contribution_pct?: string | number | null;
};

const COST_DRIVER_FIELDS: Array<{
  key: keyof FinanceTrendCostPoint;
  name: string;
  genitiveGrowth: string;
}> = [
  { key: "logistics", name: "Логистика", genitiveGrowth: "роста логистических расходов" },
  { key: "commission", name: "Комиссия WB", genitiveGrowth: "роста комиссии WB" },
  { key: "advertisement", name: "Продвижение", genitiveGrowth: "роста расходов на продвижение" },
  { key: "storage_fee", name: "Хранение", genitiveGrowth: "роста расходов на хранение" },
  { key: "penalties", name: "Штрафы", genitiveGrowth: "роста штрафов" },
  { key: "deductions", name: "Удержания", genitiveGrowth: "роста удержаний WB" },
  { key: "acquiring", name: "Эквайринг", genitiveGrowth: "роста эквайринга" },
  { key: "other", name: "Прочее", genitiveGrowth: "роста прочих расходов" },
];

const DAY_COST_KEYS: Array<{ key: keyof DailyTotalCostRow; name: string; accusative: string }> = [
  { key: "commission", name: "Комиссия WB", accusative: "комиссия WB" },
  { key: "logistics", name: "Логистика", accusative: "логистика" },
  { key: "advertisement", name: "Продвижение", accusative: "продвижение" },
  { key: "storage", name: "Хранение", accusative: "хранение" },
  { key: "penalties", name: "Штрафы", accusative: "штрафы" },
  { key: "deductions", name: "Удержания", accusative: "удержания" },
  { key: "acquiring", name: "Эквайринг", accusative: "эквайринг" },
  { key: "other", name: "Прочее", accusative: "прочее" },
];

const COST_CATEGORY_NA: Record<string, string> = {
  "Комиссия WB": "комиссию WB",
  Логистика: "логистику",
  Продвижение: "продвижение",
  Возвраты: "возвраты",
  Хранение: "хранение",
  Штрафы: "штрафы",
  Удержания: "удержания",
  Эквайринг: "эквайринг",
  Прочее: "прочее",
};

/** Relative drop vs average worth naming. */
const REL_DROP_WATCH_PCT = 15;
const REL_DROP_ALERT_PCT = 30;

/** Day total vs period average. */
const COST_SPIKE_RATIO_WATCH = 1.5;
const COST_SPIKE_RATIO_ALERT = 2;

/** Single-category dominance on a day. */
const DAY_DOMINANT_SHARE_PCT = 80;

/** Top SKU contribution attention. */
const SKU_DEPENDENCY_WATCH_PCT = 25;
const SKU_DEPENDENCY_ALERT_PCT = 40;

function num(value: string | number | null | undefined): number | null {
  if (value == null || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

/** Format chart/API date as DD.MM for seller captions. */
export function formatInsightDay(date: string): string {
  const raw = date.trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(raw)) {
    return `${raw.slice(8, 10)}.${raw.slice(5, 7)}`;
  }
  if (/^\d{2}-\d{2}$/.test(raw)) {
    return `${raw.slice(3, 5)}.${raw.slice(0, 2)}`;
  }
  return raw;
}

/** Normalize date keys for joining revenue vs finance trends. */
export function insightDateKey(date: string): string {
  const raw = date.trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(raw)) return raw.slice(0, 10);
  if (/^\d{2}-\d{2}$/.test(raw)) return raw;
  return raw;
}

function mean(values: number[]): number | null {
  if (!values.length) return null;
  return values.reduce((s, v) => s + v, 0) / values.length;
}

function timesWording(ratio: number): string {
  const rounded = Math.round(ratio * 10) / 10;
  if (rounded === 2) return "в 2 раза";
  if (Number.isInteger(rounded)) return `в ${rounded} раза`;
  return `в ${rounded.toFixed(1).replace(".", ",")} раза`;
}

function costPointByDate(
  costPoints: FinanceTrendCostPoint[] | null | undefined,
  date: string,
): FinanceTrendCostPoint | null {
  if (!costPoints?.length) return null;
  const key = insightDateKey(date);
  const suffix = key.length >= 5 ? key.slice(-5) : key;
  for (const p of costPoints) {
    const pk = insightDateKey(p.date);
    if (pk === key || pk.slice(-5) === suffix || key.slice(-5) === pk.slice(-5)) return p;
  }
  return null;
}

function avgCostField(
  costPoints: FinanceTrendCostPoint[],
  field: keyof FinanceTrendCostPoint,
): number {
  const vals: number[] = [];
  for (const p of costPoints) {
    const v = num(p[field] as string | number | null | undefined);
    if (v != null) vals.push(v);
  }
  return mean(vals) ?? 0;
}

/**
 * Strongest driver for a weak day: cost category with largest increase vs period avg,
 * or revenue drop if larger than any cost spike.
 */
function strongestDriver(
  focusDate: string,
  focusRevenue: number | null,
  avgRevenue: number | null,
  costPoints: FinanceTrendCostPoint[] | null | undefined,
): { genitiveGrowth: string; name: string } | null {
  const dayCosts = costPointByDate(costPoints, focusDate);
  let bestCost: { delta: number; genitiveGrowth: string; name: string } | null = null;

  if (dayCosts && costPoints?.length) {
    for (const field of COST_DRIVER_FIELDS) {
      const dayVal = num(dayCosts[field.key] as string | number | null | undefined) ?? 0;
      const avgVal = avgCostField(costPoints, field.key);
      const delta = dayVal - avgVal;
      if (delta <= 0) continue;
      if (!bestCost || delta > bestCost.delta) {
        bestCost = { delta, genitiveGrowth: field.genitiveGrowth, name: field.name };
      }
    }
  }

  const revenueDrop =
    focusRevenue != null && avgRevenue != null && avgRevenue > 0
      ? Math.max(0, avgRevenue - focusRevenue)
      : 0;

  if (revenueDrop > 0 && (!bestCost || revenueDrop >= bestCost.delta)) {
    return { genitiveGrowth: "снижения выручки", name: "Выручка" };
  }
  if (bestCost && bestCost.delta > 0) {
    return { genitiveGrowth: bestCost.genitiveGrowth, name: bestCost.name };
  }
  return null;
}

/**
 * Revenue / profit chart insight: FACT + DRIVER + ATTENTION vs period average.
 */
export function revenueProfitInsight(
  points: RevenueTrendInsightPoint[] | null | undefined,
  canShowProfit: boolean,
  costPoints?: FinanceTrendCostPoint[] | null,
): string | null {
  if (!points?.length) return null;

  type Row = { date: string; value: number; revenue: number | null };
  const rows: Row[] = [];

  for (const p of points) {
    if (canShowProfit) {
      const profit = num(p.seller_profit ?? p.net_profit);
      if (profit == null) continue;
      rows.push({ date: p.date, value: profit, revenue: num(p.revenue) });
    } else {
      const revenue = num(p.revenue);
      if (revenue == null) continue;
      rows.push({ date: p.date, value: revenue, revenue });
    }
  }
  if (!rows.length) return null;

  const avg = mean(rows.map((r) => r.value));
  if (avg == null) return null;

  // Focus: largest relative drop below period average (business risk day).
  let worst: { row: Row; dropPct: number } | null = null;
  for (const row of rows) {
    if (avg === 0) continue;
    const dropPct = ((avg - row.value) / Math.abs(avg)) * 100;
    if (dropPct < REL_DROP_WATCH_PCT) continue;
    if (!worst || dropPct > worst.dropPct) worst = { row, dropPct };
  }

  const metric = canShowProfit ? "прибыль" : "выручка";
  const avgRevenue = mean(rows.map((r) => r.revenue).filter((v): v is number => v != null));

  if (worst) {
    const pct = Math.round(worst.dropPct);
    const day = formatInsightDay(worst.row.date);
    const driver = strongestDriver(worst.row.date, worst.row.revenue, avgRevenue, costPoints);
    const fact = `${day} ${metric} снизилась на ${pct}% относительно среднего уровня периода`;
    const driverPart = driver ? ` из-за ${driver.genitiveGrowth}` : "";
    const attention =
      worst.dropPct >= REL_DROP_ALERT_PCT
        ? " Стоит проверить этот день."
        : " Имеет смысл обратить внимание.";
    return `${fact}${driverPart}.${attention}`;
  }

  // No material drop: report peak day only if clearly above average.
  let best: { row: Row; upPct: number } | null = null;
  for (const row of rows) {
    if (avg === 0) continue;
    const upPct = ((row.value - avg) / Math.abs(avg)) * 100;
    if (upPct < REL_DROP_WATCH_PCT) continue;
    if (!best || upPct > best.upPct) best = { row, upPct };
  }
  if (best) {
    const pct = Math.round(best.upPct);
    const day = formatInsightDay(best.row.date);
    return `${day} ${metric} выше среднего уровня периода на ${pct}%. Без критичных отклонений вниз.`;
  }

  return `За период ${metric} без резких отклонений относительно среднего уровня.`;
}

/**
 * Cost structure: largest category share + concentration attention.
 */
export function costStructureInsight(composition: PeriodCostComposition): string | null {
  const top = composition.slices[0];
  if (!top || composition.total <= 0) return null;

  const pct = Math.round(top.sharePct);
  const fact = `${top.name} занимает ${pct}% всех расходов и является крупнейшей статьёй затрат.`;

  if (top.sharePct >= 55) {
    return `${fact} Статья доминирует в структуре расходов — стоит проверить тарифы и объём.`;
  }
  if (top.sharePct >= 40) {
    return `${fact} Высокая концентрация — проверьте влияние этой статьи на маржу.`;
  }
  if (top.sharePct >= 25) {
    return fact;
  }
  return `Расходы распределены: лидер ${top.name} — ${pct}%, без доминирующей статьи.`;
}

function dominantDayCategory(row: DailyTotalCostRow): {
  name: string;
  accusative: string;
  sharePct: number;
} | null {
  if (row.total_costs <= 0) return null;
  let best: { name: string; accusative: string; amount: number } | null = null;
  for (const cat of DAY_COST_KEYS) {
    const amount = Number(row[cat.key]) || 0;
    if (!best || amount > best.amount) {
      best = { name: cat.name, accusative: cat.accusative, amount };
    }
  }
  if (!best || best.amount <= 0) return null;
  return {
    name: best.name,
    accusative: best.accusative,
    sharePct: (best.amount / row.total_costs) * 100,
  };
}

/**
 * Daily total costs: spike vs average + dominant category on that day.
 */
export function costDynamicsInsight(rows: DailyTotalCostRow[]): string | null {
  const positive = rows.filter((r) => r.total_costs > 0);
  if (!positive.length) return null;

  let peak: DailyTotalCostRow | null = null;
  for (const row of positive) {
    if (!peak || row.total_costs > peak.total_costs) peak = row;
  }
  if (!peak) return null;

  const avg = mean(positive.map((r) => r.total_costs));
  if (avg == null || avg <= 0) return null;

  const ratio = peak.total_costs / avg;
  const day = formatInsightDay(peak.date);
  const dom = dominantDayCategory(peak);
  const share = dom ? Math.round(dom.sharePct) : null;

  if (dom && dom.sharePct >= DAY_DOMINANT_SHARE_PCT) {
    return `${day} почти все расходы дня составила ${dom.accusative} (${share}%).`;
  }

  if (ratio >= COST_SPIKE_RATIO_ALERT) {
    const driver = dom ? ` Основная статья — ${dom.name.toLowerCase()}.` : "";
    return `${day} расходы были ${timesWording(ratio)} выше среднего уровня периода.${driver}`;
  }

  if (ratio >= COST_SPIKE_RATIO_WATCH) {
    const pctAbove = Math.round((ratio - 1) * 100);
    const driver = dom ? ` Основная статья — ${dom.name.toLowerCase()}.` : "";
    return `${day} расходы выше среднего на ${pctAbove}%.${driver}`;
  }

  if (dom) {
    const na = COST_CATEGORY_NA[dom.name] ?? dom.accusative;
    return `${day} пик затрат периода; основная статья — ${na} (${share}%).`;
  }
  return `${day} пик затрат относительно остальных дней периода.`;
}

/** Top SKU: contribution + dependency attention. */
export function topSkuInsight(items: TopSkuInsightItem[] | null | undefined): string | null {
  const lead = items?.[0];
  if (!lead?.sku) return null;
  const pct = num(lead.contribution_pct);
  if (pct == null || pct <= 0) return null;
  const rounded = Math.round(pct);
  const label = lead.sku.length > 48 ? `${lead.sku.slice(0, 45)}…` : lead.sku;
  const fact = `${label} формирует ${rounded}% выручки периода.`;

  if (rounded >= SKU_DEPENDENCY_ALERT_PCT) {
    return `${fact} Бизнес существенно зависит от одного товара.`;
  }
  if (rounded >= SKU_DEPENDENCY_WATCH_PCT) {
    return `${fact} Доля заметная — следите за остатками и маржой этого SKU.`;
  }
  return `${fact} Концентрация выручки в норме.`;
}
