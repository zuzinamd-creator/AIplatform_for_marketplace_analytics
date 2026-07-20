/**
 * Ledger UI design tokens (Phase 9.18-R5 / R6-P0).
 * Single source for light + dark. Tailwind maps consume these HEX values.
 *
 * WCAG AA targets: text ≥ 4.5:1 on canvas/panel; large metrics/icons ≥ 3:1.
 * Neutral scale must never equal action / profit / expense / risk / warn.
 */

export const LEDGER_LIGHT = {
  action: "#0B6BCB",
  actionHover: "#0958A8",
  actionSoft: "#E8F2FC",
  profit: "#0F7B5A",
  profitSoft: "#E6F5EF",
  expense: "#3D4A5C",
  expenseSoft: "#EEF1F4",
  risk: "#C81E1E",
  riskSoft: "#FDECEC",
  /** Darkened from #B86E00 for AA on warnSoft (text ≥4.5:1). */
  warn: "#9A5A00",
  warnSoft: "#FFF6E5",
  /** Neutral scale (tables, borders, secondary text) */
  neutral900: "#111827",
  neutral700: "#3F4B5A",
  neutral500: "#6B7280",
  neutral300: "#D1D5DB",
  neutral100: "#F3F4F6",
  canvas: "#F7F8FA",
  panel: "#FFFFFF",
  hairline: "#E6E8EC",
  inset: "#F1F3F5",
  /** Chart series (no purple; action blue not used as category fill) */
  seriesRevenue: "#2F6FED",
  seriesProfit: "#0F7B5A",
  seriesCommission: "#0F766E",
  seriesLogistics: "#A16207",
  seriesPromotion: "#1D4E89",
  seriesReturns: "#C81E1E",
  seriesStorage: "#7C5E10",
  seriesOther: "#5B6573",
  seriesPenalties: "#9F1239",
  seriesExpenseTotal: "#3D4A5C",
} as const;

/** Dark canvas: same accent roles, AA-tuned surfaces/ink. */
export const LEDGER_DARK = {
  action: "#3B8DD9",
  actionHover: "#5BA3E3",
  /** Darkened from #0F2A45 for AA with action on soft (text ≥4.5:1). */
  actionSoft: "#0A1F35",
  profit: "#34B08A",
  profitSoft: "#0F2E24",
  expense: "#9AA6B5",
  expenseSoft: "#1C2430",
  risk: "#F07171",
  riskSoft: "#3A1515",
  warn: "#E0A23A",
  warnSoft: "#3A2A0E",
  neutral900: "#F3F4F6",
  neutral700: "#D1D5DB",
  neutral500: "#9CA3AF",
  neutral300: "#374151",
  neutral100: "#1F2937",
  canvas: "#0B0F14",
  panel: "#141A22",
  hairline: "#243041",
  inset: "#1A222D",
  seriesRevenue: "#5B9BFF",
  seriesProfit: "#34B08A",
  seriesCommission: "#2DD4BF",
  seriesLogistics: "#D4A017",
  seriesPromotion: "#6BA3D9",
  seriesReturns: "#F07171",
  seriesStorage: "#C4A35A",
  seriesOther: "#9AA6B5",
  seriesPenalties: "#FB7185",
  seriesExpenseTotal: "#9AA6B5",
} as const;

export type LedgerTokenKey = keyof typeof LEDGER_LIGHT;

/** Trust badge placement contract (P0): exactly one surface on Overview. */
export const TRUST_BADGE_SPEC = {
  /** Canonical test id / landmark */
  testId: "trust-badge",
  /** Host component */
  host: "PrimaryAnswer",
  /** Placement: directly under Primary Answer metrics, static, no animation */
  placement: "under-primary-answer" as const,
  /** Must not also appear as Action Strip trust-blocker when this badge is shown */
  omitActionTrustBlocker: true,
} as const;
