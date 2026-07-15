import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { DashboardPage } from "./DashboardPage";
import { USER_ROLE_PLATFORM_ADMIN, USER_ROLE_SELLER } from "../../state/userRoles";

const dashboardSummary = vi.fn();
const useAuthMock = vi.fn();

vi.mock("../../state/http", () => ({
  api: {
    dashboard: {
      summary: (...args: unknown[]) => dashboardSummary(...args),
    },
  },
}));

vi.mock("../../state/auth", () => ({
  useAuth: () => useAuthMock(),
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
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: ReactNode }) => <div data-testid="dashboard-bar-chart">{children}</div>,
  Bar: ({ children }: { children?: ReactNode }) => <div data-testid="dashboard-bar">{children}</div>,
  LabelList: () => <div data-testid="bar-label-list" />,
  Legend: () => null,
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

const baseSummary = {
  revenue_summary: {
    kpis: { total_revenue: "1000", total_profit: null, margin_pct: null, profitability_pct: null },
    integrity: { warnings: [], profit_metrics_trust: "insufficient" },
    freshness: { stale_data_warning: false, data_as_of: "2026-05-14" },
  },
  finance_summary: { kpis: { gross_profit: null, margin_pct: null, profitability_pct: null, promotion_expenses: "0" } },
  cost_coverage: { covered_skus: 0, total_skus: 5, avg_cost_coverage_pct: "0", missing_skus: ["SKU-1"] },
  revenue_trend_daily: { points: [{ date: "2026-05-01", revenue: "100", net_profit: null, seller_profit: null }] },
  finance_trend_daily: { points: [] },
  top_skus: {
    items: [
      {
        sku: "SKU-TOP",
        revenue: "500",
        net_profit: "120",
        margin_pct: "24",
        units_sold: 3,
        contribution_pct: "50",
      },
    ],
  },
  coverage: { available_min_date: null, available_max_date: null, missing_periods: [], recommendations: [] },
  queue: { status_counts: { queued: 2 } },
  recommendations: { items: [{ id: "r1" }] },
  runtime: { rebuild: { running: 1, pending_dispatch: 0 } },
  ai_ops: { degraded_intelligence_mode: true },
  todays_focus: { dangerous: [] },
};

describe("DashboardPage trust integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthMock.mockReturnValue({
      user: { id: "u1", email: "seller@test.local", role: USER_ROLE_SELLER },
      token: "t",
      loading: false,
    });
    dashboardSummary.mockResolvedValue(baseSummary);
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

  it("still mounts FinancialSummaryCard after extract", async () => {
    renderPage();
    expect(await screen.findByText(/Финансовая сводка/i)).toBeTruthy();
  });

  it("B1: hides technical ops KPIs from sellers", async () => {
    renderPage();
    await screen.findByText(/Финансовая аналитика продавца/i);
    expect(screen.queryByText("Обработка данных")).toBeNull();
    expect(screen.queryByText(/Пересборки активны/i)).toBeNull();
    expect(screen.queryByText(/Осторожный режим/i)).toBeNull();
    expect(screen.queryByText(/Обычный режим/i)).toBeNull();
  });

  it("B1: shows technical ops KPIs for platform_admin", async () => {
    useAuthMock.mockReturnValue({
      user: { id: "a1", email: "admin@test.local", role: USER_ROLE_PLATFORM_ADMIN },
      token: "t",
      loading: false,
    });
    renderPage();
    expect(await screen.findByText("Обработка данных")).toBeTruthy();
    expect(screen.getByText(/Пересборки активны или в очереди/i)).toBeTruthy();
    expect(screen.getByText("Рекомендации ИИ")).toBeTruthy();
    expect(screen.getByText(/Задач в очереди/i)).toBeTruthy();
  });

  it("B2: has single header AI CTA to recommendations", async () => {
    renderPage();
    await screen.findByText(/Финансовая аналитика продавца/i);
    const links = screen.getAllByRole("link").filter((el) => el.className.includes("btn-accent"));
    expect(links).toHaveLength(1);
    expect(links[0].textContent).toMatch(/ИИ-помощник/);
    expect(links[0].getAttribute("href")).toBe("/app/ai/recommendations");
    expect(screen.queryByText("ИИ-анализ периода")).toBeNull();
    expect(screen.queryByRole("button", { name: /ИИ-анализ/i })).toBeNull();
  });

  it("B3: uses sales/profit bar chart title", async () => {
    renderPage();
    expect(
      await screen.findByText(/Тренд продаж и прибыли до учета операционных расходов и налогообложения/i),
    ).toBeTruthy();
    expect(screen.getAllByTestId("dashboard-bar-chart").length).toBeGreaterThanOrEqual(1);
  });

  it("B4: shows Top SKU revenue, profit and margin (gated)", async () => {
    renderPage();
    const sku = await screen.findByText("SKU-TOP");
    const row = sku.closest("div")?.parentElement;
    expect(row?.textContent).toMatch(/Прибыль:\s*—/);
    expect(row?.textContent).toMatch(/Маржа:\s*—/);
  });

  it("C1: renders on-bar labels for sales chart when period is short", async () => {
    renderPage();
    await screen.findByText(/Тренд продаж и прибыли до учета операционных расходов/i);
    expect(screen.getAllByTestId("bar-label-list").length).toBeGreaterThanOrEqual(1);
  });

  it("C2: costs chart is a bar chart with Russian footer legend", async () => {
    renderPage();
    expect(await screen.findByText("Затраты и возвраты (по дням)")).toBeTruthy();
    expect(screen.getAllByTestId("dashboard-bar-chart").length).toBe(2);
    expect(screen.getByText(/Логистика · Продвижение · Возвраты · Выплаты/i)).toBeTruthy();
  });
});
