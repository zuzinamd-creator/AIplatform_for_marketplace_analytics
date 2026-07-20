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
const isOnboardingDoneMock = vi.fn();

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
  isOnboardingDone: () => isOnboardingDoneMock(),
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
  Cell: () => null,
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
  recommendations: { items: [], page: { total: 1, skip: 0, limit: 0 } },
  runtime: { rebuild: { running: 1, pending_dispatch: 0 } },
  ai_ops: { degraded_intelligence_mode: true },
  todays_focus: { dangerous: [] },
};

describe("DashboardPage trust integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    isOnboardingDoneMock.mockReturnValue(true);
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

  it("F2-A2: renders PrimaryAnswer with revenue, profit and TrustChip", async () => {
    renderPage();
    const block = await screen.findByTestId("primary-answer");
    expect(block.querySelector(".text-ink-muted")?.textContent).toMatch(/Выручка/);
    expect(block.textContent).toMatch(/Чистая прибыль/);
    expect(block.querySelector('[data-testid="trust-chip"]')).toBeTruthy();
    expect(screen.getByTestId("trust-chip-cta").getAttribute("href")).toBe("/app/costs");
  });

  it("F2-A2: reduces duplicate trust surfaces on dashboard", async () => {
    renderPage();
    await screen.findByTestId("primary-answer");
    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(screen.queryByText(/Себестоимость 0 %/)).toBeNull();
    expect(screen.getAllByTestId("trust-chip")).toHaveLength(1);
    expect(screen.queryByText("Продажи (выбранный период)")).toBeNull();
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

  it("B1: shows admin system section collapsed below fold", async () => {
    useAuthMock.mockReturnValue({
      user: { id: "a1", email: "admin@test.local", role: USER_ROLE_PLATFORM_ADMIN },
      token: "t",
      loading: false,
    });
    renderPage();
    const adminSection = await screen.findByTestId("dashboard-admin-system");
    expect(adminSection.hasAttribute("open")).toBe(false);
    fireEvent.click(screen.getByText("Система"));
    expect(adminSection.hasAttribute("open")).toBe(true);
    expect(await screen.findByTestId("dashboard-admin-kpis")).toBeTruthy();
    expect(screen.getByText("Обработка данных")).toBeTruthy();
    expect(screen.getByText(/Пересборки активны или в очереди/i)).toBeTruthy();
    expect(screen.getByText("Рекомендации ИИ")).toBeTruthy();
    expect(screen.getByText(/Задач в очереди/i)).toBeTruthy();
    const secondaryLinks = screen.getByTestId("dashboard-secondary-links");
    expect(
      adminSection.compareDocumentPosition(secondaryLinks) & Node.DOCUMENT_POSITION_PRECEDING,
    ).toBeTruthy();
  });

  it("F2-A2: secondary links below fold replace header CTAs", async () => {
    renderPage();
    await screen.findByText(/Финансовая аналитика продавца/i);
    expect(screen.queryByText("Загрузить отчёт")).toBeNull();
    expect(screen.queryByRole("link", { name: /Подробное сравнение периодов/i })).toBeNull();
    const secondary = screen.getByTestId("dashboard-secondary-links");
    expect(secondary.querySelector('a[href="/app/analytics/weekly"]')?.textContent).toMatch(
      /Сравнение периодов/,
    );
    expect(secondary.querySelector('a[href="/app/economics"]')?.textContent).toMatch(/Экономика SKU/);
    expect(secondary.querySelector('a[href="/app/ai/recommendations"]')?.textContent).toMatch(
      /ИИ-помощник/,
    );
    expect(screen.queryByText("ИИ-анализ периода")).toBeNull();
    expect(screen.queryByRole("button", { name: /ИИ-анализ/i })).toBeNull();
  });

  it("B3: uses sales/profit bar chart title", async () => {
    renderPage();
    expect(await screen.findByText(/Выручка и прибыль по дням/i)).toBeTruthy();
    expect(screen.getAllByTestId("dashboard-bar-chart").length).toBeGreaterThanOrEqual(1);
  });

  it("F2-A2: TopSkusCard appears before revenue chart", async () => {
    renderPage();
    await screen.findByText("SKU-TOP");
    const topSkuHeading = screen.getByText("Топ SKU");
    const chartHeading = screen.getByText(/Выручка и прибыль по дням/i);
    expect(
      chartHeading.compareDocumentPosition(topSkuHeading) & Node.DOCUMENT_POSITION_PRECEDING,
    ).toBeTruthy();
  });

  it("F2-A2: removes Daily Scenario and Trust section", async () => {
    renderPage();
    await screen.findByTestId("primary-answer");
    expect(screen.queryByText("Ежедневный сценарий и доверие к данным")).toBeNull();
    expect(screen.queryByText("Ежедневный сценарий")).toBeNull();
    expect(screen.queryByText("Завершить настройку →")).toBeNull();
  });

  it("B4: shows Top SKU revenue, units, profit and margin (gated)", async () => {
    renderPage();
    expect(await screen.findByText("SKU-TOP")).toBeTruthy();
    expect(screen.getByText(/3 шт\./)).toBeTruthy();
    expect(screen.getAllByText(/Прибыль:\s*—/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Маржа SKU/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: /В Экономику товаров/i }).getAttribute("href")).toBe(
      "/app/economics",
    );
    expect(screen.getByRole("tab", { name: "Выручка" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Прибыль" })).toBeTruthy();
    expect(screen.getByRole("tab", { name: "Маржа SKU" })).toBeTruthy();
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
    fireEvent.click(screen.getByRole("tab", { name: "Маржа SKU" }));
    expect(await screen.findByText("SKU-MARGIN")).toBeTruthy();
    expect(topSkus).toHaveBeenCalledWith(expect.objectContaining({ sort: "margin", limit: 5 }));
    expect(screen.getByText("Требует внимания")).toBeTruthy();
  });

  it("C1: renders on-bar labels for sales chart when period is short", async () => {
    renderPage();
    await screen.findByText(/Выручка и прибыль по дням/i);
    expect(screen.getAllByTestId("bar-label-list").length).toBeGreaterThanOrEqual(1);
  });

  it("C2: cost structure shows period composition and daily total costs", async () => {
    renderPage();
    expect(await screen.findByTestId("cost-composition-legend")).toBeTruthy();
    expect(screen.getByText("Структура расходов за период")).toBeTruthy();
    expect(screen.getByText("Общие затраты по дням")).toBeTruthy();
    expect(screen.getByText(/Комиссия WB:/)).toBeTruthy();
    expect(screen.getByText(/Удержания:/)).toBeTruthy();
    expect(screen.getByText(/Прочие списания WB/i)).toBeTruthy();
    expect(screen.getAllByTestId("dashboard-bar-chart").length).toBeGreaterThanOrEqual(2);
    const totalBars = screen
      .getAllByTestId("dashboard-bar")
      .filter((el) => el.getAttribute("data-key") === "total_costs");
    expect(totalBars.length).toBe(1);
    expect(totalBars[0].getAttribute("data-name")).toBe("Затраты");
    expect(screen.queryByText("Выплаты")).toBeNull();
    expect(screen.getByTestId("daily-costs-period-strip")).toBeTruthy();
    expect(screen.getByTestId("daily-costs-share-note").textContent).toMatch(
      /% — доля от общей суммы расходов за период/,
    );
    expect(screen.getAllByTestId("cost-share-note").length).toBeGreaterThanOrEqual(1);
    const structureInsight = screen.getByTestId("cost-structure-insight");
    expect(structureInsight.textContent).toMatch(/занимает \d+% всех расходов/);
    expect(screen.getByTestId("cost-dynamics-insight")).toBeTruthy();
    expect(screen.getByTestId("top-sku-insight").textContent).toMatch(/формирует 50% выручки периода/);
    expect(screen.getByTestId("dashboard-insight-line")).toBeTruthy();
    expect(screen.getAllByText(/Маржа по выплате/i).length).toBeGreaterThanOrEqual(1);
  });

  it("F2-B: renders ActionStrip between PrimaryAnswer and TopSkus", async () => {
    renderPage();
    await screen.findByTestId("action-card-trust-blocker");
    const actionStrip = screen.getByTestId("action-strip");
    const topSkuHeading = screen.getByText("Топ SKU");
    expect(
      topSkuHeading.compareDocumentPosition(actionStrip) & Node.DOCUMENT_POSITION_PRECEDING,
    ).toBeTruthy();
    expect(screen.queryByText("Что требует внимания сегодня")).toBeNull();
    expect(screen.queryByTestId("business-signals-panel")).toBeNull();
  });

  it("F2-B: removes chart ProfitTrustBadge from dashboard", async () => {
    renderPage();
    await screen.findByText(/Выручка и прибыль по дням/i);
    const chartHeading = screen.getByText(/Выручка и прибыль по дням/i).closest(".p-6");
    expect(chartHeading?.textContent).not.toMatch(/Нет себестоимости/);
    expect(chartHeading?.querySelector('[aria-label*="себестоим"]')).toBeNull();
  });

  it("F2-B: shows trust-blocker and cost signal in Action Strip", async () => {
    renderPage();
    expect(await screen.findByTestId("action-card-trust-blocker")).toBeTruthy();
    expect(screen.getByTestId("action-card-signal-cost").textContent).toMatch(
      /Комиссия WB составляет 46%/,
    );
    expect(
      screen.getByTestId("action-card-signal-cost").querySelector('a[href="/app/analytics#dashboard-cost-structure"]'),
    ).toBeTruthy();
  });

  it("F2-B: shows returns and SKU action cards when trust allows", async () => {
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
      recommendations: { items: [], page: { total: 0, skip: 0, limit: 0 } },
    });
    renderPage();
    expect(await screen.findByTestId("action-card-signal-returns")).toBeTruthy();
    expect(screen.getByTestId("action-card-signal-returns").textContent).toMatch(/Возвраты достигли 12%/);
    expect(screen.getByTestId("action-card-signal-sku").textContent).toMatch(
      /SKU SKU-WEAK имеет высокую выручку при низкой марже/,
    );
    expect(screen.queryByTestId("action-card-trust-blocker")).toBeNull();
  });

  it("F2-B.1: hides FirstRunChecklist when onboarding is done", async () => {
    isOnboardingDoneMock.mockReturnValue(true);
    renderPage();
    await screen.findByTestId("primary-answer");
    expect(screen.queryByText(/Первый запуск: чек‑лист продавца/i)).toBeNull();
  });

  it("F2-B.1: above-fold blocks follow F1.6 order", async () => {
    renderPage();
    const fold = await screen.findByTestId("dashboard-above-fold");
    const period = screen.getByTestId("period-selector");
    const primary = screen.getByTestId("primary-answer");
    const actions = screen.getByTestId("action-strip");
    const topSkus = screen.getByTestId("top-skus-card");
    expect(fold.contains(period)).toBe(true);
    expect(fold.contains(primary)).toBe(true);
    expect(fold.contains(actions)).toBe(true);
    expect(fold.contains(topSkus)).toBe(true);
    expect(
      primary.compareDocumentPosition(period) & Node.DOCUMENT_POSITION_PRECEDING,
    ).toBeTruthy();
    expect(
      actions.compareDocumentPosition(primary) & Node.DOCUMENT_POSITION_PRECEDING,
    ).toBeTruthy();
    expect(
      topSkus.compareDocumentPosition(actions) & Node.DOCUMENT_POSITION_PRECEDING,
    ).toBeTruthy();
  });

  it("F2-B.1: removes page subtitle per F1.6", async () => {
    renderPage();
    await screen.findByTestId("primary-answer");
    expect(screen.queryByText(/Обзор бизнеса: KPI, риски и доверие/i)).toBeNull();
  });

  it("F2-B.1: dashboard trust surfaces match F1.6 allowlist", async () => {
    renderPage();
    await screen.findByTestId("primary-answer");
    expect(screen.getAllByTestId("trust-chip")).toHaveLength(1);
    expect(screen.queryByRole("progressbar")).toBeNull();
    expect(screen.queryByText(/Доверие к прибыли/i)).toBeNull();
    expect(screen.queryByText(/Покрытие себестоимости/i)).toBeNull();
    expect(screen.queryByText("Что требует внимания сегодня")).toBeNull();
    const chartHeading = screen.getByText(/Выручка и прибыль по дням/i).closest(".p-6");
    expect(chartHeading?.textContent).not.toMatch(/Нет себестоимости/);
  });

  it("F2-B: shows empty state when no action sources match", async () => {
    dashboardSummary.mockResolvedValue({
      ...baseSummary,
      revenue_summary: {
        ...baseSummary.revenue_summary,
        integrity: { warnings: [], profit_metrics_trust: "full" },
      },
      finance_summary: {
        kpis: {
          ...baseSummary.finance_summary.kpis,
          commission: "0",
          logistics: "0",
          advertisement: "0",
          storage_fee: "0",
          penalties: "0",
          deductions: "0",
          acquiring: "0",
          returns_amount: "0",
          return_rate_pct: "0",
        },
      },
      top_skus: { items: [] },
      recommendations: { items: [], page: { total: 0, skip: 0, limit: 0 } },
      todays_focus: { dangerous: [] },
    });
    renderPage();
    expect(await screen.findByTestId("action-card-empty")).toBeTruthy();
    expect(screen.getByText("Сейчас без срочных действий")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Открыть брифинг" }).getAttribute("href")).toBe("/app/today");
  });
});
