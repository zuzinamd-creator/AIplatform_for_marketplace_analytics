import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { AnalyticsHubPage } from "./AnalyticsHubPage";
import {
  ANALYTICS_COST_COVERAGE_ROUTE,
  ANALYTICS_ECONOMICS_ROUTE,
  ANALYTICS_WEEKLY_ROUTE,
} from "../../shell/analytics-tabs";

describe("AnalyticsHubPage (legacy fallback)", () => {
  it("renders analytics entry with links to hub tab routes", () => {
    render(
      <MemoryRouter>
        <AnalyticsHubPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Аналитика" })).toBeTruthy();
    expect(screen.getByRole("link", { name: /Обзор бизнеса/i }).getAttribute("href")).toBe("/app/dashboard");
    expect(screen.getByRole("link", { name: /Сравнение периодов/i }).getAttribute("href")).toBe(
      ANALYTICS_WEEKLY_ROUTE,
    );
    expect(screen.getByRole("link", { name: /Экономика SKU/i }).getAttribute("href")).toBe(ANALYTICS_ECONOMICS_ROUTE);
    expect(screen.getByRole("link", { name: /Покрытие себестоимости/i }).getAttribute("href")).toBe(
      ANALYTICS_COST_COVERAGE_ROUTE,
    );
  });
});
