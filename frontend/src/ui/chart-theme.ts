/** Shared Recharts styling tokens (visual only). */
export const CHART = {
  axis: { fill: "#94a3b8", fontSize: 12 },
  grid: { stroke: "#e2e8f0", strokeDasharray: "4 4" },
  tooltip: {
    background: "rgba(255, 255, 255, 0.98)",
    border: "1px solid #e2e8f0",
    borderRadius: 10,
    color: "#0f172a",
    fontSize: 12,
    padding: "8px 12px",
  },
  series: {
    revenue: "#3b82f6",
    profit: "#059669",
    logistics: "#ca8a04",
    ads: "#7c3aed",
    returns: "#e11d48",
    payout: "#4f46e5",
    spark: "#059669",
  },
} as const;
