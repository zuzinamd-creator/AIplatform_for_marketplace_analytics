/** Shared Recharts styling tokens (visual only). */
export const CHART = {
  /** Axis ticks: ink-secondary for WCAG-friendly contrast on white panels (was slate-400). */
  axis: { fill: "#334155", fontSize: 12 },
  /** On-bar / end labels on cost charts */
  barLabel: { fill: "#0f172a", fontSize: 11, fontWeight: 600 },
  grid: { stroke: "#e2e8f0", strokeDasharray: "4 4" },
  tooltip: {
    background: "rgba(255, 255, 255, 0.98)",
    border: "1px solid #e2e8f0",
    borderRadius: 10,
    color: "#0f172a",
    fontSize: 12,
    padding: "8px 12px",
  },
  /** Category axis width for vertical cost bars (Russian labels e.g. «Комиссия WB»). */
  costCategoryAxisWidth: 132,
  series: {
    revenue: "#3b82f6",
    profit: "#059669",
    logistics: "#ca8a04",
    ads: "#7c3aed",
    returns: "#e11d48",
    payout: "#4f46e5",
    spark: "#059669",
    commission: "#0d9488",
    storage: "#d97706",
    penalties: "#dc2626",
    deductions: "#9333ea",
    acquiring: "#2563eb",
    other: "#64748b",
    otherCosts: "#64748b",
    /** Single-series daily total costs (Phase 9.15-B). */
    costTotal: "#475569",
  },
} as const;
