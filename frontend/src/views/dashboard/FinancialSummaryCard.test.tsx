import { describe, expect, it, afterEach } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";

import { deriveProfitTrustContext } from "../../state/profit-trust";
import type { FinancialKpiSummaryResponse } from "../../state/types-analytics";
import { FinancialSummaryCard } from "./FinancialSummaryCard";
import { MARGIN_PAYOUT_HINT, MARGIN_PAYOUT_LABEL } from "./margin-labels";

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
    { covered_skus: 5, total_skus: 5, avg_cost_coverage_pct: "100", missing_skus: [] },
  );
}

function trustPartial() {
  return deriveProfitTrustContext(
    { warnings: [], profit_metrics_trust: "partial" },
    { covered_skus: 3, total_skus: 5, avg_cost_coverage_pct: "60", missing_skus: ["A"] },
  );
}

function trustInsufficient() {
  return deriveProfitTrustContext(
    { warnings: [], profit_metrics_trust: "insufficient" },
    { covered_skus: 0, total_skus: 5, avg_cost_coverage_pct: "0", missing_skus: ["A"] },
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

describe("FinancialSummaryCard R19 UX", () => {
  afterEach(() => {
    cleanup();
  });

  it("uses seller-facing labels: Выплата от WB and Маржа по выплате", () => {
    renderCard({ kpis: { commission: "1200" } });
    expect(screen.getByText(/Финансовая сводка/i)).toBeTruthy();
    expect(screen.getByText("Выплата от WB")).toBeTruthy();
    expect(screen.getByText("Комиссия WB")).toBeTruthy();
    expect(screen.getByText(MARGIN_PAYOUT_LABEL)).toBeTruthy();
    expect(screen.getByLabelText(MARGIN_PAYOUT_HINT)).toBeTruthy();
    expect(screen.getByText("Чистая прибыль")).toBeTruthy();
    expect(screen.getByText("Деньги от Wildberries")).toBeTruthy();
    expect(screen.getByText("Расходы WB")).toBeTruthy();
    expect(screen.queryByText("Прибыль")).toBeNull();
    expect(screen.getByText("Удержания WB")).toBeTruthy();
    expect(screen.queryByText(/Settlement/i)).toBeNull();
    expect(screen.queryByText("Маржинальность")).toBeNull();
    expect(screen.queryByText(/^Маржа$/)).toBeNull();
  });

  it("shows WB expenses flat without services accordion", () => {
    renderCard({ kpis: { commission: "1200", logistics: "1000", storage_fee: "100" } });
    expect(screen.queryByText(/Детализация услуг WB/i)).toBeNull();
    expect(screen.getByText("Комиссия WB")).toBeTruthy();
    expect(screen.getByText("Логистика")).toBeTruthy();
    expect(screen.getByText("Хранение")).toBeTruthy();
    expect(screen.getByText("Удержания WB")).toBeTruthy();

    const wbSection = screen.getByText("Деньги от Wildberries").closest("section");
    expect(wbSection).toBeTruthy();
    const labels = ["Выручка", "К перечислению за товар", "Комиссия WB", "Логистика", "Хранение", "Удержания WB", "Выплата от WB"];
    const text = wbSection?.textContent ?? "";
    let last = -1;
    for (const label of labels) {
      const idx = text.indexOf(label);
      expect(idx).toBeGreaterThan(last);
      last = idx;
    }
  });

  it("keeps allowed disclosures closed by default", () => {
    const { container } = renderCard({
      kpis: {
        promotion_expenses: "9925",
        jam_subscription_expenses: "500",
        manual_expenses_total: "10425",
      },
    });
    const details = container.querySelectorAll("details");
    // Из них + Ещё показатели only (no services accordion)
    expect(details.length).toBe(2);
    for (const el of details) {
      expect(el.open).toBe(false);
    }
    expect(screen.queryByText(/Детализация услуг WB/i)).toBeNull();
    expect(screen.getByText(/^Из них$/i)).toBeTruthy();
    expect(screen.getByText(/Ещё показатели/i)).toBeTruthy();
  });

  it("A: hides WB and Jam rows when both are zero", () => {
    renderCard({
      kpis: {
        promotion_expenses: "0",
        jam_subscription_expenses: "0",
        manual_expenses_total: "0",
      },
    });
    expect(screen.queryByText(/^Из них$/i)).toBeNull();
    expect(screen.queryByText(/WB-продвижение/i)).toBeNull();
    expect(screen.queryByText(/Подписка Джем/i)).toBeNull();
  });

  it("B: shows only WB-продвижение under Из них when jam is zero", () => {
    renderCard({
      kpis: {
        promotion_expenses: "9925",
        jam_subscription_expenses: "0",
        manual_expenses_total: "9925",
      },
    });
    expect(screen.getByText(/^Из них$/i)).toBeTruthy();
    expect(screen.getByText(/WB-продвижение/i)).toBeTruthy();
    expect(screen.queryByText(/Подписка Джем/i)).toBeNull();
  });

  it("C: shows only Подписка Джем under Из них when WB is zero", () => {
    renderCard({
      kpis: {
        promotion_expenses: "0",
        jam_subscription_expenses: "500",
        manual_expenses_total: "500",
      },
    });
    expect(screen.getByText(/^Из них$/i)).toBeTruthy();
    expect(screen.getByText(/Подписка Джем/i)).toBeTruthy();
    expect(screen.queryByText(/WB-продвижение/i)).toBeNull();
  });

  it("D: promo/jam under Из них; logistics visible without accordion", () => {
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
    const izNikh = screen.getByText(/^Из них$/i).closest("details");
    expect(izNikh).toBeTruthy();
    expect(within(izNikh as HTMLElement).getByText(/WB-продвижение/i)).toBeTruthy();
    expect(within(izNikh as HTMLElement).getByText(/Подписка Джем/i)).toBeTruthy();

    expect(screen.queryByText(/Детализация услуг WB/i)).toBeNull();
    expect(screen.getByText("Логистика")).toBeTruthy();
    expect(screen.getByText("Хранение")).toBeTruthy();
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
    expect(screen.getByText(/~.*45/)).toBeTruthy();
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });
});
