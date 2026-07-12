import { describe, expect, it, afterEach } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { AnalyticsShell } from "./AnalyticsShell";
import {
  ANALYTICS_COST_COVERAGE_ROUTE,
  ANALYTICS_ECONOMICS_ROUTE,
  ANALYTICS_OVERVIEW_ROUTE,
  ANALYTICS_WEEKLY_ROUTE,
} from "./analytics-tabs";

function renderShell(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/app/analytics" element={<AnalyticsShell />}>
          <Route index element={<div>overview-panel</div>} />
          <Route path="weekly" element={<div>weekly-panel</div>} />
          <Route path="economics" element={<div>economics-panel</div>} />
          <Route path="cost-coverage" element={<div>cost-coverage-panel</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("AnalyticsShell", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders hub title and all four analytics tabs", () => {
    renderShell(ANALYTICS_OVERVIEW_ROUTE);

    expect(screen.getByRole("heading", { name: "Аналитика" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Обзор" }).getAttribute("href")).toBe(ANALYTICS_OVERVIEW_ROUTE);
    expect(screen.getByRole("link", { name: "Сравнение периодов" }).getAttribute("href")).toBe(
      ANALYTICS_WEEKLY_ROUTE,
    );
    expect(screen.getByRole("link", { name: "Экономика SKU" }).getAttribute("href")).toBe(
      ANALYTICS_ECONOMICS_ROUTE,
    );
    expect(screen.getByRole("link", { name: "Покрытие себестоимости" }).getAttribute("href")).toBe(
      ANALYTICS_COST_COVERAGE_ROUTE,
    );
  });

  it("renders overview tab content by default", () => {
    renderShell(ANALYTICS_OVERVIEW_ROUTE);
    expect(screen.getByText("overview-panel")).toBeTruthy();
  });

  it("renders weekly tab content at /app/analytics/weekly", () => {
    renderShell(ANALYTICS_WEEKLY_ROUTE);
    expect(screen.getByText("weekly-panel")).toBeTruthy();
  });

  it("renders economics tab content at /app/analytics/economics", () => {
    renderShell(ANALYTICS_ECONOMICS_ROUTE);
    expect(screen.getByText("economics-panel")).toBeTruthy();
  });

  it("renders cost coverage tab content at /app/analytics/cost-coverage", () => {
    renderShell(ANALYTICS_COST_COVERAGE_ROUTE);
    expect(screen.getByText("cost-coverage-panel")).toBeTruthy();
  });
});
