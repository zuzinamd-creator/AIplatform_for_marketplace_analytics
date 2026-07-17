/** Deterministic one-line chart insights (Phase 9.15-B). No AI. */

import type { PeriodCostComposition } from "./cost-structure-chart";
import type { DailyTotalCostRow } from "./cost-structure-chart";

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

/**
 * Revenue / profit chart insight.
 * Prefer max profit day when profit is shown; else max revenue day.
 */
export function revenueProfitInsight(
  points: RevenueTrendInsightPoint[] | null | undefined,
  canShowProfit: boolean,
): string | null {
  if (!points?.length) return null;

  if (canShowProfit) {
    let best: { date: string; profit: number } | null = null;
    for (const p of points) {
      const profit = num(p.seller_profit ?? p.net_profit);
      if (profit == null) continue;
      if (!best || profit > best.profit) best = { date: p.date, profit };
    }
    if (best && best.profit > 0) {
      return `Максимальная прибыль была ${formatInsightDay(best.date)}.`;
    }
  }

  let bestRev: { date: string; revenue: number } | null = null;
  for (const p of points) {
    const revenue = num(p.revenue);
    if (revenue == null || revenue <= 0) continue;
    if (!bestRev || revenue > bestRev.revenue) bestRev = { date: p.date, revenue };
  }
  if (!bestRev) return null;
  return `Пик выручки: ${formatInsightDay(bestRev.date)}.`;
}

/** Dominant-share threshold: clear leader without quoting the %. */
const COST_STRUCTURE_LEADER_SHARE_PCT = 40;

/** Below this, treat as distributed (no clear leader). */
const COST_STRUCTURE_WEAK_LEADER_SHARE_PCT = 25;

/** Accusative after «на …» for seller-facing category names. */
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

/**
 * Cost structure chart insight — contextual only (Phase 9.15-B2).
 * Must not repeat Business Signals' «{name} составляет {pct}% …» wording.
 */
export function costStructureInsight(composition: PeriodCostComposition): string | null {
  const top = composition.slices[0];
  if (!top || composition.total <= 0) return null;

  if (top.sharePct >= COST_STRUCTURE_LEADER_SHARE_PCT) {
    const na = COST_CATEGORY_NA[top.name] ?? top.name.toLowerCase();
    return `Основная часть расходов приходится на ${na}.`;
  }

  if (top.sharePct >= COST_STRUCTURE_WEAK_LEADER_SHARE_PCT && composition.slices.length >= 1) {
    return "Структура расходов концентрирована вокруг одной статьи затрат.";
  }

  if (composition.slices.length >= 2) {
    return "Расходы распределены между несколькими категориями без явного лидера.";
  }

  return null;
}

/** Cost dynamics: peak total-cost day. */
export function costDynamicsInsight(rows: DailyTotalCostRow[]): string | null {
  let best: DailyTotalCostRow | null = null;
  for (const row of rows) {
    if (row.total_costs <= 0) continue;
    if (!best || row.total_costs > best.total_costs) best = row;
  }
  if (!best) return null;
  return `Пик расходов пришёлся на ${formatInsightDay(best.date)}.`;
}

/** Top SKU: contribution of the first (leader) row. */
export function topSkuInsight(items: TopSkuInsightItem[] | null | undefined): string | null {
  const lead = items?.[0];
  if (!lead?.sku) return null;
  const pct = num(lead.contribution_pct);
  if (pct == null || pct <= 0) return null;
  const rounded = Math.round(pct);
  const label = lead.sku.length > 48 ? `${lead.sku.slice(0, 45)}…` : lead.sku;
  return `${label} формирует ${rounded}% выручки периода.`;
}
