import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { WeeklyAnalysisPage } from "./WeeklyAnalysisPage";

const periodCompare = vi.fn();
const abcAnalysis = vi.fn();
const inventoryRisk = vi.fn();
const inventoryEconomics = vi.fn();
const warehouseAnalytics = vi.fn();
const costCoverage = vi.fn();

vi.mock("../../state/http", () => ({
  api: {
    analytics: {
      periodCompare: (...args: unknown[]) => periodCompare(...args),
      abcAnalysis: (...args: unknown[]) => abcAnalysis(...args),
      inventoryRisk: (...args: unknown[]) => inventoryRisk(...args),
      inventoryEconomics: (...args: unknown[]) => inventoryEconomics(...args),
      warehouseAnalytics: (...args: unknown[]) => warehouseAnalytics(...args),
      costCoverage: (...args: unknown[]) => costCoverage(...args),
    },
  },
}));

vi.mock("../../state/onboarding", () => ({
  loadWorkspaceProfile: () => ({ workspace_name: "Test", marketplace: "wildberries" }),
}));

vi.mock("../../state/period", async () => {
  const actual = await vi.importActual<typeof import("../../state/period")>("../../state/period");
  return {
    ...actual,
    loadPeriodSelection: () => ({
      preset: "14d" as const,
      range: { start: "2026-05-01", end: "2026-05-14" },
      compareEnabled: true,
      comparePreset: "previous_period" as const,
    }),
  };
});

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <WeeklyAnalysisPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("WeeklyAnalysisPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    periodCompare.mockResolvedValue({
      marketplace: "wildberries",
      a_start: "2026-05-01",
      a_end: "2026-05-14",
      b_start: "2026-04-17",
      b_end: "2026-04-30",
      a: { total_revenue: "1000", total_profit: "200", margin_pct: "20", units_sold: 50 },
      b: { total_revenue: "800", total_profit: "150", margin_pct: "18", units_sold: 40 },
      delta_revenue: "200",
      delta_profit: "50",
      delta_margin_pct: "2",
      freshness: { stale_data_warning: false },
      integrity: { warnings: [], profit_metrics_trust: "full", sku_cost_coverage_pct: "100" },
    });
    costCoverage.mockResolvedValue({
      total_skus: 10,
      covered_skus: 10,
      sku_cost_coverage_pct: "100",
      missing_skus: [],
    });
    abcAnalysis.mockResolvedValue({
      buckets: [
        { bucket: "A", sku_count: 5, revenue: "800", revenue_pct: "80" },
        { bucket: "B", sku_count: 10, revenue: "150", revenue_pct: "15" },
        { bucket: "C", sku_count: 20, revenue: "50", revenue_pct: "5" },
      ],
      freshness: { stale_data_warning: false },
    });
    inventoryRisk.mockResolvedValue({
      snapshot_date: "2026-05-14",
      high_discrepancy_warehouses: 1,
      discrepancy_cost_total: "100",
      stale_data_warning: false,
      freshness: { stale_data_warning: false },
    });
    inventoryEconomics.mockResolvedValue({
      items: [
        { sku: "SKU-1", stock_units: 0, sold_units: 10, stock_risk: "stockout", frozen_capital: "0" },
        { sku: "SKU-2", stock_units: 500, sold_units: 1, stock_risk: "overstock", frozen_capital: "5000" },
      ],
      freshness: { stale_data_warning: false },
    });
    warehouseAnalytics.mockResolvedValue({
      snapshot_date: "2026-05-14",
      semantics_version: "1.0",
      items: [
        {
          warehouse_name: "WH-1",
          opening_stock: 10,
          inbound_units: 0,
          sold_units: 3,
          returned_units: 0,
          lost_units: 0,
          writeoff_units: 0,
          expected_closing_stock: 7,
          actual_stock: 6,
          discrepancy_units: -1,
          discrepancy_cost: "50",
          discrepancy_sale_value: "100",
        },
      ],
      freshness: { stale_data_warning: false },
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("renders weekly analysis sections and calls analytics APIs", async () => {
    renderPage();

    expect(screen.getByRole("heading", { name: "Сравнение периодов", level: 1 })).toBeTruthy();
    const backLink = screen.getByRole("link", { name: "Вернуться к обзору бизнеса" });
    expect(backLink.getAttribute("href")).toBe("/app/dashboard");
    expect(await screen.findByText("ABC-анализ")).toBeTruthy();
    expect(await screen.findByText("Риски запасов")).toBeTruthy();
    expect(await screen.findByText("Складская аналитика")).toBeTruthy();

    await waitFor(() => {
      expect(periodCompare).toHaveBeenCalled();
      expect(costCoverage).toHaveBeenCalled();
      expect(abcAnalysis).toHaveBeenCalled();
      expect(inventoryRisk).toHaveBeenCalled();
      expect(inventoryEconomics).toHaveBeenCalled();
      expect(warehouseAnalytics).toHaveBeenCalled();
    });
  });

  it("shows ABC buckets and warehouse table", async () => {
    renderPage();

    expect(await screen.findByText("Группа A")).toBeTruthy();
    expect(await screen.findByText("Группа B")).toBeTruthy();
    expect(await screen.findByText("Группа C")).toBeTruthy();
    expect(await screen.findByText("WH-1")).toBeTruthy();
  });

  it("blocks profit priority and shows trust badge when COGS trust is insufficient", async () => {
    periodCompare.mockResolvedValue({
      marketplace: "wildberries",
      a_start: "2026-05-01",
      a_end: "2026-05-14",
      b_start: "2026-04-17",
      b_end: "2026-04-30",
      a: { total_revenue: "1000", total_profit: null, margin_pct: null, units_sold: 50 },
      b: { total_revenue: "800", total_profit: null, margin_pct: null, units_sold: 40 },
      delta_revenue: "200",
      delta_profit: "0",
      delta_margin_pct: null,
      freshness: { stale_data_warning: false },
      integrity: { warnings: [], profit_metrics_trust: "insufficient" },
    });
    costCoverage.mockResolvedValue({
      total_skus: 5,
      covered_skus: 0,
      sku_cost_coverage_pct: "0",
      missing_skus: ["SKU-1"],
    });

    renderPage();

    expect(await screen.findByLabelText(/Загрузите себестоимость/i)).toBeTruthy();
    expect(screen.queryByText(/Прибыль снизилась относительно предыдущего периода/i)).toBeNull();
  });
});
