/** Shared Recharts styling — Ledger UI chart tokens (no purple categorical fills). */
import { LEDGER_LIGHT } from "./design-tokens";

export const CHART = {
  axis: { fill: LEDGER_LIGHT.neutral700, fontSize: 12 },
  barLabel: { fill: LEDGER_LIGHT.neutral900, fontSize: 11, fontWeight: 600 },
  grid: { stroke: LEDGER_LIGHT.hairline, strokeDasharray: "4 4" },
  tooltip: {
    background: "rgba(255, 255, 255, 0.98)",
    border: `1px solid ${LEDGER_LIGHT.hairline}`,
    borderRadius: 10,
    color: LEDGER_LIGHT.neutral900,
    fontSize: 12,
    padding: "8px 12px",
  },
  costCategoryAxisWidth: 132,
  series: {
    revenue: LEDGER_LIGHT.seriesRevenue,
    profit: LEDGER_LIGHT.seriesProfit,
    logistics: LEDGER_LIGHT.seriesLogistics,
    ads: LEDGER_LIGHT.seriesPromotion,
    returns: LEDGER_LIGHT.seriesReturns,
    payout: LEDGER_LIGHT.expense,
    spark: LEDGER_LIGHT.seriesProfit,
    commission: LEDGER_LIGHT.seriesCommission,
    storage: LEDGER_LIGHT.seriesStorage,
    penalties: LEDGER_LIGHT.seriesPenalties,
    deductions: LEDGER_LIGHT.seriesOther,
    acquiring: LEDGER_LIGHT.seriesOther,
    other: LEDGER_LIGHT.seriesOther,
    otherCosts: LEDGER_LIGHT.seriesOther,
    costTotal: LEDGER_LIGHT.seriesExpenseTotal,
  },
} as const;
