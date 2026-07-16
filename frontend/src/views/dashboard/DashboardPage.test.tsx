import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { DashboardPage } from "./DashboardPage";
import { USER_ROLE_PLATFORM_ADMIN, USER_ROLE_SELLER } from "../../state/userRoles";

const dashboardSummary = vi.fn();
const topSkus = vi.fn();
const useAuthMock = vi.fn();

vi.mock("../../state/http", () => ({
  api: {
    dashboard: {
      summary: (...args: unknown[]) => dashboardSummary(...args),
    },
    analytics: {
      topSkus: (...args: unknown[]) => topSkus(...args),
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
  Bar: ({
    children,
    name,
    dataKey,
    stackId,
  }: {
    children?: ReactNode;
    name?: string;
    dataKey?: string;
    stackId?: string;
  }) => (
    <div
      data-testid="dashboard-bar"
      data-name={name ?? ""}
      data-key={dataKey ?? ""}
      data-stack={stackId ?? ""}
    >
      {children}
    </div>
  ),
  LabelList: () => <div data-testid="bar-label-list" />,
  Legend: () => <div data-testid="dashboard-legend" />,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => <div data-testid="dashboard-tooltip" />,
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
  finance_summary: {
    kpis: {
      sales_revenue: "1000",
      returns_amount: "50",
      return_rate_pct: "5",
      commission: "430",
      logistics: "200",
      advertisement: "100",
      storage_fee: "50",
      penalties: "0",
      deductions: "100",
      acquiring: "50",
      gross_profit: null,
      margin_pct: null,
      profitability_pct: null,
      promotion_expenses: "0",
    },
  },
  cost_coverage: { covered_skus: 0, total_skus: 5, avg_cost_coverage_pct: "0", missing_skus: ["SKU-1"] },
  revenue_trend_daily: { points: [{ date: "2026-05-01", revenue: "100", net_profit: null, seller_profit: null }] },
  finance_trend_daily: {
    points: [
      {
        date: "2026-05-01",
        sales_revenue: "100",
        logistics: "10",
        advertisement: "20",
        returns_amount: "5",
        payout: "80",
        commission: "15",
        storage_fee: "1",
        penalties: "2",
        deductions: "3",
        acquiring: "4",
        other: "0",
      },
    ],
  },
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
    topSkus.mockResolvedValue({
      items: [
        {
          sku: "SKU-PROFIT",
          revenue: "400",
          net_profit: "200",
          margin_pct: "50",
          units_sold: 8,
          contribution_pct: "40",
        },
      ],
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

  it("B4: shows Top SKU revenue, units, profit and margin (gated)", async () => {
    renderPage();
    expect(await screen.findByText("SKU-TOP")).toBeTruthy();
    expect(screen.getByText(/3 шт\./)).toBeTruthy();
    expect(screen.getAllByText(/Прибыль:\s*—/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Маржа:\s*—/).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /В Экономику товаров/i }).getAttribute("href")).toBe(
      "/app/economics",
    );
    expect(screen.getByRole("tab", { name: "Выручка" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Прибыль" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Маржа" })).toBeTruthy();
    expect(topSkus).not.toHaveBeenCalled();
  });

  it("E1: profit tab calls top-skus API with sort=profit", async () => {
    renderPage();
    await screen.findByText("SKU-TOP");
    fireEvent.click(screen.getByRole("tab", { name: "Прибыль" }));
    expect(await screen.findByText("SKU-PROFIT")).toBeTruthy();
    expect(topSkus).toHaveBeenCalledWith(
      expect.objectContaining({
        marketplace: "wildberries",
        start: "2026-05-01",
        end: "2026-05-14",
        limit: 5,
        sort: "profit",
      }),
    );
  });

  it("E1: margin tab calls top-skus API with sort=margin and highlights attention", async () => {
    topSkus.mockResolvedValue({
      items: [
        {
          sku: "SKU-MARGIN",
          revenue: "1000",
          net_profit: "50",
          margin_pct: "5",
          units_sold: 2,
        },
      ],
    });
    renderPage();
    await screen.findByText("SKU-TOP");
    fireEvent.click(screen.getByRole("tab", { name: "Маржа" }));
    expect(await screen.findByText("SKU-MARGIN")).toBeTruthy();
    expect(topSkus).toHaveBeenCalledWith(expect.objectContaining({ sort: "margin", limit: 5 }));
    expect(screen.getByText("Требует внимания")).toBeTruthy();
  });

  it("C1: renders on-bar labels for sales chart when period is short", async () => {
    renderPage();
    await screen.findByText(/Тренд продаж и прибыли до учета операционных расходов/i);
    expect(screen.getAllByTestId("bar-label-list").length).toBeGreaterThanOrEqual(1);
  });

  it("C2: cost structure stacked chart without payout", async () => {
    renderPage();
    expect(await screen.findByText("Структура расходов и возвратов")).toBeTruthy();
    expect(screen.getAllByTestId("dashboard-bar-chart").length).toBe(2);
    expect(screen.getAllByTestId("dashboard-legend").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByTestId("dashboard-tooltip").length).toBeGreaterThanOrEqual(1);
    expect(
      screen.getByText(
        /Комиссия · Логистика · Продвижение · Возвраты · Хранение · Штрафы · Удержания · Эквайринг/i,
      ),
    ).toBeTruthy();

    const costBars = screen
      .getAllByTestId("dashboard-bar")
      .filter((el) => el.getAttribute("data-stack") === "cost-structure");
    expect(costBars).toHaveLength(8);
    expect(costBars.map((el) => el.getAttribute("data-name"))).toEqual([
      "Комиссия",
      "Логистика",
      "Продвижение",
      "Возвраты",
      "Хранение",
      "Штрафы",
      "Удержания",
      "Эквайринг",
    ]);
    expect(costBars.every((el) => el.getAttribute("data-key") !== "payout")).toBe(true);
    expect(costBars.every((el) => el.getAttribute("data-key") !== "other_costs")).toBe(true);
    expect(screen.queryByText("Выплаты")).toBeNull();
    expect(screen.queryByText("Прочие расходы")).toBeNull();
  });

  it("B13: shows cost business signal and hides SKU signal when trust insufficient", async () => {
    renderPage();
    expect(await screen.findByTestId("business-signals-panel")).toBeTruthy();
    expect(screen.getByText("Бизнес-сигналы")).toBeTruthy();
    expect(screen.getByTestId("business-signal-cost").textContent).toMatch(/Комиссия WB составляет 46%/);
    expect(screen.queryByTestId("business-signal-returns")).toBeNull();
    expect(screen.queryByTestId("business-signal-sku")).toBeNull();
  });

  it("B13: shows returns and SKU signals when trust allows and thresholds met", async () => {
    dashboardSummary.mockResolvedValue({
      ...baseSummary,
      revenue_summary: {
        ...baseSummary.revenue_summary,
        integrity: { warnings: [], profit_metrics_trust: "full" },
      },
      finance_summary: {
        kpis: {
          ...baseSummary.finance_summary.kpis,
          sales_revenue: "1000",
          returns_amount: "120",
          return_rate_pct: "12",
          commission: "100",
          logistics: "50",
        },
      },
      top_skus: {
        items: [
          { sku: "SKU-A", revenue: "100000", net_profit: "20000", margin_pct: "20", units_sold: 1 },
          { sku: "SKU-WEAK", revenue: "80000", net_profit: "500", margin_pct: "0.6", units_sold: 1 },
        ],
      },
    });
    renderPage();
    expect(await screen.findByTestId("business-signal-returns")).toBeTruthy();
    expect(screen.getByTestId("business-signal-returns").textContent).toMatch(/Возвраты достигли 12%/);
    expect(screen.getByTestId("business-signal-sku").textContent).toMatch(
      /SKU SKU-WEAK имеет высокую выручку при низкой марже/,
    );
  });
});
