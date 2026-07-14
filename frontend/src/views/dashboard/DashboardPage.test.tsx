import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { DashboardPage } from "./DashboardPage";

const dashboardSummary = vi.fn();

vi.mock("../../state/http", () => ({
  api: {
    dashboard: {
      summary: (...args: unknown[]) => dashboardSummary(...args),
    },
    ai: {
      runIntelligenceForPeriod: vi.fn(),
    },
  },
}));

vi.mock("../../state/onboarding", () => ({
  loadWorkspaceProfile: () => ({ workspace_name: "Test", marketplace: "wildberries" }),
}));

vi.mock("../../state/settings", () => ({
  isDemoMode: () => false,
}));

vi.mock("../../state/usage", () => ({
  trackUsage: vi.fn(),
}));

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  LineChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
}));

vi.mock("../../state/period", async () => {
  const actual = await vi.importActual<typeof import("../../state/period")>("../../state/period");
  return {
    ...actual,
    loadPeriodSelection: () => ({
      preset: "14d" as const,
      range: { start: "2026-05-01", end: "2026-05-14" },
      compareEnabled: false,
    }),
  };
});

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DashboardPage trust integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    dashboardSummary.mockResolvedValue({
      revenue_summary: {
        kpis: { total_revenue: "1000", total_profit: null, margin_pct: null, profitability_pct: null },
        integrity: { warnings: [], profit_metrics_trust: "insufficient" },
        freshness: { stale_data_warning: false, data_as_of: "2026-05-14" },
      },
      finance_summary: { kpis: { gross_profit: null, margin_pct: null, profitability_pct: null, promotion_expenses: "0" } },
      cost_coverage: { covered_skus: 0, total_skus: 5, sku_cost_coverage_pct: "0", missing_skus: ["SKU-1"] },
      revenue_trend_daily: { points: [{ date: "2026-05-01", revenue: "100", net_profit: null, seller_profit: null }] },
      finance_trend_daily: { points: [] },
      top_skus: { items: [] },
      coverage: { available_min_date: null, available_max_date: null, missing_periods: [], recommendations: [] },
      queue: { status_counts: {} },
      recommendations: { items: [] },
      runtime: { rebuild: {} },
      ai_ops: {},
      todays_focus: { dangerous: [] },
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("hides profit KPI values when trust is insufficient", async () => {
    renderPage();
    expect(await screen.findByText(/Финансовая аналитика продавца/i)).toBeTruthy();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Нет себестоимости/i).length).toBeGreaterThan(0);
  });

  it("does not show inline period compare teaser on overview", async () => {
    renderPage();
    await screen.findByText(/Финансовая аналитика продавца/i);
    expect(screen.queryByText(/Δвыручка/i)).toBeNull();
    expect(dashboardSummary).toHaveBeenCalledWith(
      expect.objectContaining({
        marketplace: "wildberries",
        start: "2026-05-01",
        end: "2026-05-14",
      }),
    );
    expect(dashboardSummary.mock.calls[0][0]).not.toHaveProperty("compare_start");
  });
});

function mockFinanceSummary(kpis: Record<string, string | null>) {
  dashboardSummary.mockResolvedValue({
    revenue_summary: {
      kpis: { total_revenue: "100000", total_profit: "20000", margin_pct: "20", profitability_pct: "50" },
      integrity: { warnings: [], profit_metrics_trust: "full" },
      freshness: { stale_data_warning: false, data_as_of: "2026-05-14" },
    },
    finance_summary: {
      kpis: {
        payout_for_goods: "80000",
        logistics: "1000",
        storage_fee: "100",
        deductions: "500",
        total_to_pay: "75000",
        cogs: "30000",
        gross_profit: "20000",
        seller_profit_raw: "45000",
        adjusted_settlement: "65000",
        margin_pct: "20",
        profitability_pct: "50",
        promotion_expenses: "0",
        jam_subscription_expenses: "0",
        manual_expenses_total: "0",
        ...kpis,
      },
    },
    cost_coverage: { covered_skus: 5, total_skus: 5, sku_cost_coverage_pct: "100", missing_skus: [] },
    revenue_trend_daily: { points: [{ date: "2026-05-01", revenue: "100", net_profit: "10", seller_profit: "10" }] },
    finance_trend_daily: { points: [] },
    top_skus: { items: [] },
    coverage: { available_min_date: null, available_max_date: null, missing_periods: [], recommendations: [] },
    queue: { status_counts: {} },
    recommendations: { items: [] },
    runtime: { rebuild: {} },
    ai_ops: {},
    todays_focus: { dangerous: [] },
  });
}

describe("DashboardPage Task 0 manual expense rows", () => {
  afterEach(() => {
    cleanup();
  });

  it("A: hides WB and Jam rows when both are zero", async () => {
    mockFinanceSummary({
      promotion_expenses: "0",
      jam_subscription_expenses: "0",
      manual_expenses_total: "0",
    });
    renderPage();
    await screen.findByText(/Финансовая сводка/i);
    expect(screen.queryByText("WB-продвижение")).toBeNull();
    expect(screen.queryByText("Подписка Джем")).toBeNull();
    expect(screen.queryByText(/Затраты на продвижение/i)).toBeNull();
  });

  it("B: shows only WB-продвижение when jam is zero", async () => {
    mockFinanceSummary({
      promotion_expenses: "9925",
      jam_subscription_expenses: "0",
      manual_expenses_total: "9925",
    });
    renderPage();
    expect(await screen.findByText("WB-продвижение")).toBeTruthy();
    expect(screen.queryByText("Подписка Джем")).toBeNull();
  });

  it("C: shows only Подписка Джем when WB is zero", async () => {
    mockFinanceSummary({
      promotion_expenses: "0",
      jam_subscription_expenses: "500",
      manual_expenses_total: "500",
    });
    renderPage();
    expect(await screen.findByText("Подписка Джем")).toBeTruthy();
    expect(screen.queryByText("WB-продвижение")).toBeNull();
  });

  it("D: shows both WB and Jam rows when both are positive", async () => {
    mockFinanceSummary({
      promotion_expenses: "9925",
      jam_subscription_expenses: "500",
      manual_expenses_total: "10425",
    });
    renderPage();
    expect(await screen.findByText("WB-продвижение")).toBeTruthy();
    expect(screen.getByText("Подписка Джем")).toBeTruthy();
    expect(screen.getByText(/Settlement WB \(после ручных расходов\)/i)).toBeTruthy();
  });
});
