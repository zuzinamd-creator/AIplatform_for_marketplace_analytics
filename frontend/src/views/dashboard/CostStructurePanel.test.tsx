import { describe, expect, it, vi, afterEach } from "vitest";
import type { ReactNode } from "react";
import { cleanup, render, screen } from "@testing-library/react";

import { CHART } from "../../ui/chart-theme";
import { CostStructurePanel } from "./CostStructurePanel";

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  BarChart: ({
    children,
    margin,
  }: {
    children: ReactNode;
    margin?: { top?: number; right?: number; left?: number; bottom?: number };
  }) => (
    <div
      data-testid="cost-bar-chart"
      data-margin-right={String(margin?.right ?? "")}
      data-margin-left={String(margin?.left ?? "")}
    >
      {children}
    </div>
  ),
  Bar: ({ children }: { children?: ReactNode }) => <div data-testid="cost-bar">{children}</div>,
  LabelList: ({ dataKey }: { dataKey?: string }) => (
    <div data-testid="cost-structure-share-labels" data-key={dataKey ?? ""} />
  ),
  Cell: () => null,
  XAxis: () => null,
  YAxis: ({ width, interval }: { width?: number; interval?: number }) => (
    <div
      data-testid={interval === 0 ? "cost-structure-yaxis" : "cost-daily-yaxis"}
      data-width={String(width ?? "")}
      data-interval={String(interval ?? "")}
      data-tick-fill={CHART.axis.fill}
    />
  ),
  Tooltip: () => null,
}));

describe("CostStructurePanel labels", () => {
  afterEach(() => {
    cleanup();
  });

  const kpis = {
    commission: "460",
    logistics: "200",
    advertisement: "100",
    returns_amount: "50",
    storage_fee: "40",
    penalties: "0",
    deductions: "80",
    acquiring: "30",
    other: "40",
  };

  it("renders category legend with names, rubles and percentages", () => {
    render(
      <CostStructurePanel
        periodStart="2026-07-01"
        periodEnd="2026-07-07"
        financeKpis={kpis}
        trendPoints={[{ date: "2026-07-01", commission: "100", logistics: "50" }]}
      />,
    );

    expect(screen.getByTestId("cost-structure-chart")).toBeTruthy();
    expect(screen.getByTestId("cost-composition-legend").textContent).toMatch(/Комиссия WB:/);
    expect(screen.getByTestId("cost-composition-legend").textContent).toMatch(/%/);
    expect(screen.getByTestId("cost-legend-commission").textContent).toMatch(/Комиссия WB/);
  });

  it("configures YAxis wide enough for Russian labels and shows share LabelList", () => {
    render(
      <CostStructurePanel
        periodStart="2026-07-01"
        periodEnd="2026-07-07"
        financeKpis={kpis}
        trendPoints={null}
      />,
    );

    const yAxis = screen.getByTestId("cost-structure-yaxis");
    expect(Number(yAxis.getAttribute("data-width"))).toBeGreaterThanOrEqual(CHART.costCategoryAxisWidth);
    expect(yAxis.getAttribute("data-interval")).toBe("0");
    expect(yAxis.getAttribute("data-tick-fill")).toBe("#3F4B5A");

    const labels = screen.getByTestId("cost-structure-share-labels");
    expect(labels.getAttribute("data-key")).toBe("sharePct");

    const chart = screen.getByTestId("cost-bar-chart");
    expect(Number(chart.getAttribute("data-margin-right"))).toBeGreaterThanOrEqual(40);
  });

  it("renders daily costs chart with on-bar labels and without mismatched color strip", () => {
    render(
      <CostStructurePanel
        periodStart="2026-07-01"
        periodEnd="2026-07-07"
        financeKpis={kpis}
        trendPoints={[
          { date: "2026-07-01", commission: "100", logistics: "50" },
          { date: "2026-07-02", commission: "80", logistics: "40" },
        ]}
      />,
    );

    expect(screen.getByTestId("daily-costs-chart")).toBeTruthy();
    expect(screen.queryByTestId("daily-costs-period-strip")).toBeNull();
    expect(screen.getAllByTestId("cost-structure-share-labels").length).toBeGreaterThanOrEqual(1);
  });
});
