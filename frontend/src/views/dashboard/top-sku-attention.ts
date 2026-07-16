/** UX-only attention heuristic for Dashboard Top SKU (no business-math changes). */

export type TopSkuSortTab = "revenue" | "profit" | "margin";

export type TopSkuAttentionRow = {
  revenue: string;
  net_profit?: string | null;
  margin_pct?: string | null;
};

/**
 * High revenue (≥ 50% of max in the visible list) and weak profit or margin.
 * Null/gated profit+margin → never flagged (insufficient data, not a signal).
 */
export function skuNeedsAttention(row: TopSkuAttentionRow, peers: TopSkuAttentionRow[]): boolean {
  const rev = Number(row.revenue);
  if (!Number.isFinite(rev) || rev <= 0) return false;

  const maxRev = Math.max(
    0,
    ...peers.map((p) => Number(p.revenue)).filter((n) => Number.isFinite(n) && n > 0),
  );
  if (maxRev <= 0) return false;

  const highRevenue = rev >= maxRev * 0.5;
  const profit =
    row.net_profit == null || row.net_profit === "" ? null : Number(row.net_profit);
  const margin =
    row.margin_pct == null || row.margin_pct === "" ? null : Number(row.margin_pct);

  if (profit === null && margin === null) return false;

  const lowProfit =
    profit !== null && Number.isFinite(profit) && (profit <= 0 || profit / rev < 0.1);
  const lowMargin = margin !== null && Number.isFinite(margin) && margin < 10;

  return highRevenue && (lowProfit || lowMargin);
}

export function topSkuApiSortParam(tab: TopSkuSortTab): string {
  if (tab === "margin") return "margin";
  if (tab === "profit") return "profit";
  return "revenue";
}
