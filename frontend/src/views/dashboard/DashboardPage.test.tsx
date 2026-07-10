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
});
