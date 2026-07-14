import { describe, expect, it, afterEach } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { deriveProfitTrustContext } from "../../state/profit-trust";
import type { FinancialKpiSummaryResponse } from "../../state/types-analytics";
import { FinancialSummaryCard } from "./FinancialSummaryCard";

type FinanceKpis = FinancialKpiSummaryResponse["kpis"];

function baseKpis(overrides: Partial<FinanceKpis> = {}): FinanceKpis {
  return {
    sales_revenue: "0",
    returns_amount: "0",
    payout: "80000",
    payout_for_goods: "80000",
    commission: "0",
    logistics: "1000",
    storage_fee: "100",
    acquiring: "0",
    advertisement: "0",
    penalties: "0",
    deductions: "500",
    compensation: "0",
    cogs: "30000",
    gross_profit: "45000",
    seller_profit_raw: "45000",
    promotion_expenses: "0",
    jam_subscription_expenses: "0",
    manual_expenses_total: "0",
    adjusted_settlement: "75000",
    margin_pct: "20",
    profitability_pct: "50",
    return_rate_pct: null,
    total_to_pay: "75000",
    ...overrides,
  };
}

function trustFull() {
  return deriveProfitTrustContext(
    { warnings: [], profit_metrics_trust: "full" },
    { covered_skus: 5, total_skus: 5, sku_cost_coverage_pct: "100", missing_skus: [] },
  );
}

function trustPartial() {
  return deriveProfitTrustContext(
    { warnings: [], profit_metrics_trust: "partial" },
    { covered_skus: 3, total_skus: 5, sku_cost_coverage_pct: "60", missing_skus: ["A"] },
  );
}

function trustInsufficient() {
  return deriveProfitTrustContext(
    { warnings: [], profit_metrics_trust: "insufficient" },
    { covered_skus: 0, total_skus: 5, sku_cost_coverage_pct: "0", missing_skus: ["A"] },
  );
}

function renderCard(
  opts: {
    kpis?: Partial<FinanceKpis>;
    revenue?: string;
    trust?: ReturnType<typeof trustFull>;
  } = {},
) {
  return render(
    <FinancialSummaryCard
      periodStart="2026-06-15"
      periodEnd="2026-06-21"
      totalRevenue={opts.revenue ?? "100000"}
      financeKpis={baseKpis(opts.kpis)}
      trustCtx={opts.trust ?? trustFull()}
    />,
  );
}

describe("FinancialSummaryCard behavior freeze", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders settlement, margin, profitability labels unchanged", () => {
    renderCard();
    expect(screen.getByText(/Финансовая сводка/i)).toBeTruthy();
    expect(screen.getByText(/Settlement WB \(к перечислению\)/i)).toBeTruthy();
    expect(screen.getByText("Маржинальность")).toBeTruthy();
    expect(screen.getByText("Рентабельность")).toBeTruthy();
    expect(screen.getByText("Чистая прибыль")).toBeTruthy();
  });

  it("A: hides WB and Jam rows when both are zero", () => {
    renderCard({
      kpis: {
        promotion_expenses: "0",
        jam_subscription_expenses: "0",
        manual_expenses_total: "0",
      },
    });
    expect(screen.queryByText(/в т.ч. WB-продвижение/i)).toBeNull();
    expect(screen.queryByText(/в т.ч. Подписка Джем/i)).toBeNull();
    expect(screen.queryByText(/Затраты на продвижение/i)).toBeNull();
  });

  it("B: shows only WB-продвижение when jam is zero", () => {
    renderCard({
      kpis: {
        promotion_expenses: "9925",
        jam_subscription_expenses: "0",
        manual_expenses_total: "9925",
      },
    });
    expect(screen.getByText(/в т.ч. WB-продвижение/i)).toBeTruthy();
    expect(screen.queryByText(/в т.ч. Подписка Джем/i)).toBeNull();
  });

  it("C: shows only Подписка Джем when WB is zero", () => {
    renderCard({
      kpis: {
        promotion_expenses: "0",
        jam_subscription_expenses: "500",
        manual_expenses_total: "500",
      },
    });
    expect(screen.getByText(/в т.ч. Подписка Джем/i)).toBeTruthy();
    expect(screen.queryByText(/в т.ч. WB-продвижение/i)).toBeNull();
  });

  it("D: shows both promo/jam and settlement footnote without second-subtract row", () => {
    renderCard({
      kpis: {
        promotion_expenses: "9925",
        jam_subscription_expenses: "500",
        manual_expenses_total: "10425",
        adjusted_settlement: "75000",
        total_to_pay: "75000",
        seller_profit_raw: "45000",
        gross_profit: "45000",
      },
    });
    expect(screen.getByText(/в т.ч. WB-продвижение/i)).toBeTruthy();
    expect(screen.getByText(/в т.ч. Подписка Джем/i)).toBeTruthy();
    expect(screen.queryByText(/Settlement WB \(после ручных расходов\)/i)).toBeNull();
    expect(screen.getByText(/Settlement WB \(к перечислению\)/i)).toBeTruthy();
    expect(
      screen.getByText(/детализация удержаний \(уже внутри Settlement\), без повторного вычета/i),
    ).toBeTruthy();
  });

  it("shows profit trust badge and hides profit when COGS trust is insufficient", () => {
    renderCard({
      kpis: { gross_profit: null, margin_pct: null, profitability_pct: null, cogs: null },
      trust: trustInsufficient(),
    });
    expect(screen.getByText(/Нет себестоимости/i)).toBeTruthy();
    expect(screen.getByText(/Прибыль и маржа недоступны без себестоимости/i)).toBeTruthy();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });

  it("partial trust shows estimated profit and hides margin/profitability", () => {
    renderCard({
      kpis: {
        gross_profit: "45000",
        margin_pct: "20",
        profitability_pct: "50",
      },
      trust: trustPartial(),
    });
    expect(screen.getByText(/Прибыль показана как оценка/i)).toBeTruthy();
    // formatProfitValue prefixes ~ for partial
    expect(screen.getByText(/~.*45/)).toBeTruthy();
    // margin & profitability gated to —
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });
});
