/** Deterministic dashboard business signals from summary payload (Phase 9.13-B). */

import { skuNeedsAttention, type TopSkuAttentionRow } from "./top-sku-attention";

export const RETURNS_PRESSURE_THRESHOLD_PCT = 10;

export type ExpenseKpis = {
  commission?: string | number | null;
  logistics?: string | number | null;
  advertisement?: string | number | null;
  storage_fee?: string | number | null;
  penalties?: string | number | null;
  deductions?: string | number | null;
  acquiring?: string | number | null;
  other?: string | number | null;
};

export type BusinessSignal = {
  id: "cost" | "returns" | "sku";
  text: string;
};

function num(value: string | number | null | undefined): number {
  if (value == null || value === "") return 0;
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

const EXPENSE_CATEGORIES: Array<{ key: keyof ExpenseKpis; label: string }> = [
  { key: "commission", label: "Комиссия WB" },
  { key: "logistics", label: "Логистика" },
  { key: "advertisement", label: "Продвижение" },
  { key: "storage_fee", label: "Хранение" },
  { key: "penalties", label: "Штрафы" },
  { key: "deductions", label: "Удержания" },
  { key: "acquiring", label: "Эквайринг" },
  { key: "other", label: "Прочее" },
];

export type DominantExpense = {
  key: keyof ExpenseKpis;
  label: string;
  amount: number;
  sharePct: number;
};

/** Highest WB expense category share among fee-like costs (excludes returns/payout/COGS). */
export function dominantExpense(kpis: ExpenseKpis | null | undefined): DominantExpense | null {
  if (!kpis) return null;
  let best: DominantExpense | null = null;
  let total = 0;
  const amounts: Array<{ key: keyof ExpenseKpis; label: string; amount: number }> = [];

  for (const cat of EXPENSE_CATEGORIES) {
    const amount = num(kpis[cat.key]);
    total += amount;
    amounts.push({ key: cat.key, label: cat.label, amount });
  }
  if (total <= 0) return null;

  for (const row of amounts) {
    if (!best || row.amount > best.amount) {
      best = {
        key: row.key,
        label: row.label,
        amount: row.amount,
        sharePct: (row.amount / total) * 100,
      };
    }
  }
  return best;
}

export function buildCostStructureSignal(kpis: ExpenseKpis | null | undefined): BusinessSignal | null {
  const dom = dominantExpense(kpis);
  if (!dom || dom.amount <= 0) return null;
  const pct = Math.round(dom.sharePct);
  return {
    id: "cost",
    text: `${dom.label} составляет ${pct}% всех расходов за период.`,
  };
}

export type ReturnsInput = {
  sales_revenue?: string | number | null;
  returns_amount?: string | number | null;
  return_rate_pct?: string | number | null;
};

/** Return pressure as % of revenue; prefers return_rate_pct when present. */
export function returnsPressurePct(input: ReturnsInput | null | undefined): number | null {
  if (!input) return null;
  const rate = num(input.return_rate_pct);
  if (input.return_rate_pct != null && input.return_rate_pct !== "" && Number.isFinite(rate)) {
    return rate;
  }
  const revenue = num(input.sales_revenue);
  if (revenue <= 0) return null;
  return (num(input.returns_amount) / revenue) * 100;
}

export function buildReturnsSignal(
  input: ReturnsInput | null | undefined,
  thresholdPct: number = RETURNS_PRESSURE_THRESHOLD_PCT,
): BusinessSignal | null {
  const pct = returnsPressurePct(input);
  if (pct == null || pct <= thresholdPct) return null;
  return {
    id: "returns",
    text: `Возвраты достигли ${Math.round(pct)}% от выручки и требуют внимания.`,
  };
}

export type TopSkuSignalRow = TopSkuAttentionRow & { sku: string };

export function buildSkuAttentionSignal(
  items: TopSkuSignalRow[] | null | undefined,
  opts: { trustInsufficient: boolean },
): BusinessSignal | null {
  if (opts.trustInsufficient) return null;
  const peers = items ?? [];
  const hit = peers.find((row) => skuNeedsAttention(row, peers));
  if (!hit) return null;
  return {
    id: "sku",
    text: `SKU ${hit.sku} имеет высокую выручку при низкой марже.`,
  };
}

/** Priority: cost → returns → SKU; max 3. */
export function buildBusinessSignals(input: {
  financeKpis?: (ExpenseKpis & ReturnsInput) | null;
  topSkus?: TopSkuSignalRow[] | null;
  trustInsufficient: boolean;
}): BusinessSignal[] {
  const out: BusinessSignal[] = [];
  const cost = buildCostStructureSignal(input.financeKpis);
  if (cost) out.push(cost);
  const returns = buildReturnsSignal(input.financeKpis);
  if (returns) out.push(returns);
  const sku = buildSkuAttentionSignal(input.topSkus, {
    trustInsufficient: input.trustInsufficient,
  });
  if (sku) out.push(sku);
  return out.slice(0, 3);
}
