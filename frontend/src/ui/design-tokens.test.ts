import { describe, expect, it } from "vitest";

import { LEDGER_DARK, LEDGER_LIGHT, TRUST_BADGE_SPEC } from "./design-tokens";

function luminance(hex: string): number {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16) / 255;
  const g = parseInt(h.slice(2, 4), 16) / 255;
  const b = parseInt(h.slice(4, 6), 16) / 255;
  const lin = (c: number) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

/** Relative luminance contrast ratio (WCAG 2.x). */
export function contrast(a: string, b: string): number {
  const l1 = luminance(a);
  const l2 = luminance(b);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

const TEXT_AA = 4.5;
const LARGE_AA = 3;

type SoftPair = { name: string; fg: string; bg: string };

function softPairs(tokens: typeof LEDGER_LIGHT): SoftPair[] {
  return [
    { name: "action / actionSoft", fg: tokens.action, bg: tokens.actionSoft },
    { name: "profit / profitSoft", fg: tokens.profit, bg: tokens.profitSoft },
    { name: "expense / expenseSoft", fg: tokens.expense, bg: tokens.expenseSoft },
    { name: "risk / riskSoft", fg: tokens.risk, bg: tokens.riskSoft },
    { name: "warn / warnSoft", fg: tokens.warn, bg: tokens.warnSoft },
  ];
}

function inkOnSurfacePairs(tokens: typeof LEDGER_LIGHT): SoftPair[] {
  return [
    { name: "N900 / panel", fg: tokens.neutral900, bg: tokens.panel },
    { name: "N700 / panel", fg: tokens.neutral700, bg: tokens.panel },
    { name: "N500 / panel", fg: tokens.neutral500, bg: tokens.panel },
    { name: "N900 / canvas", fg: tokens.neutral900, bg: tokens.canvas },
    { name: "N700 / canvas", fg: tokens.neutral700, bg: tokens.canvas },
    { name: "N500 / canvas", fg: tokens.neutral500, bg: tokens.canvas },
  ];
}

function largeMetricPairs(tokens: typeof LEDGER_LIGHT): SoftPair[] {
  return [
    { name: "action / panel", fg: tokens.action, bg: tokens.panel },
    { name: "profit / panel", fg: tokens.profit, bg: tokens.panel },
    { name: "expense / panel", fg: tokens.expense, bg: tokens.panel },
    { name: "risk / panel", fg: tokens.risk, bg: tokens.panel },
    { name: "warn / panel", fg: tokens.warn, bg: tokens.panel },
  ];
}

describe("Ledger design tokens", () => {
  it("keeps neutrals distinct from semantic accents", () => {
    const accents = [
      LEDGER_LIGHT.action,
      LEDGER_LIGHT.profit,
      LEDGER_LIGHT.expense,
      LEDGER_LIGHT.risk,
      LEDGER_LIGHT.warn,
    ];
    for (const n of [
      LEDGER_LIGHT.neutral900,
      LEDGER_LIGHT.neutral700,
      LEDGER_LIGHT.neutral500,
      LEDGER_LIGHT.neutral300,
      LEDGER_LIGHT.neutral100,
    ]) {
      expect(accents).not.toContain(n);
    }
  });

  it("defines dark variants for every light key", () => {
    for (const key of Object.keys(LEDGER_LIGHT) as (keyof typeof LEDGER_LIGHT)[]) {
      expect(LEDGER_DARK[key]).toMatch(/^#[0-9A-Fa-f]{6}$/);
    }
  });

  it("forbids purple-like chart fills in light palette", () => {
    const series = [
      LEDGER_LIGHT.seriesRevenue,
      LEDGER_LIGHT.seriesProfit,
      LEDGER_LIGHT.seriesCommission,
      LEDGER_LIGHT.seriesLogistics,
      LEDGER_LIGHT.seriesPromotion,
      LEDGER_LIGHT.seriesReturns,
      LEDGER_LIGHT.seriesStorage,
      LEDGER_LIGHT.seriesOther,
      LEDGER_LIGHT.seriesPenalties,
      LEDGER_LIGHT.seriesExpenseTotal,
    ];
    for (const hex of series) {
      const h = hex.replace("#", "");
      const r = parseInt(h.slice(0, 2), 16);
      const g = parseInt(h.slice(2, 4), 16);
      const b = parseInt(h.slice(4, 6), 16);
      expect(!(b > 180 && r > 100 && g < 100)).toBe(true);
    }
  });

  it("documents Trust badge single placement", () => {
    expect(TRUST_BADGE_SPEC.testId).toBe("trust-badge");
    expect(TRUST_BADGE_SPEC.placement).toBe("under-primary-answer");
    expect(TRUST_BADGE_SPEC.omitActionTrustBlocker).toBe(true);
  });
});

describe("Ledger WCAG AA — light", () => {
  it.each(inkOnSurfacePairs(LEDGER_LIGHT))("text $name ≥ 4.5", ({ fg, bg }) => {
    expect(contrast(fg, bg)).toBeGreaterThanOrEqual(TEXT_AA);
  });

  it.each(largeMetricPairs(LEDGER_LIGHT))("large metric $name ≥ 3", ({ fg, bg }) => {
    expect(contrast(fg, bg)).toBeGreaterThanOrEqual(LARGE_AA);
  });

  it.each(softPairs(LEDGER_LIGHT))("soft surface $name ≥ 4.5", ({ fg, bg }) => {
    expect(contrast(fg, bg)).toBeGreaterThanOrEqual(TEXT_AA);
  });
});

describe("Ledger WCAG AA — dark", () => {
  it.each(inkOnSurfacePairs(LEDGER_DARK))("text $name ≥ 4.5", ({ fg, bg }) => {
    expect(contrast(fg, bg)).toBeGreaterThanOrEqual(TEXT_AA);
  });

  it.each(largeMetricPairs(LEDGER_DARK))("large metric $name ≥ 3", ({ fg, bg }) => {
    expect(contrast(fg, bg)).toBeGreaterThanOrEqual(LARGE_AA);
  });

  it.each(softPairs(LEDGER_DARK))("soft surface $name ≥ 4.5", ({ fg, bg }) => {
    expect(contrast(fg, bg)).toBeGreaterThanOrEqual(TEXT_AA);
  });
});
