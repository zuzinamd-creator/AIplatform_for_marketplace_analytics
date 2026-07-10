import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { AnalyticsHubPage } from "./AnalyticsHubPage";

describe("AnalyticsHubPage", () => {
  it("renders analytics entry with links to overview, comparison, economics, and cost coverage", () => {
    render(
      <MemoryRouter>
        <AnalyticsHubPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Аналитика" })).toBeTruthy();
    expect(screen.getByRole("link", { name: /Обзор бизнеса/i }).getAttribute("href")).toBe("/app/dashboard");
    expect(screen.getByRole("link", { name: /Сравнение периодов/i }).getAttribute("href")).toBe(
      "/app/analytics/weekly",
    );
    expect(screen.getByRole("link", { name: /Экономика SKU/i }).getAttribute("href")).toBe("/app/economics");
    expect(screen.getByRole("link", { name: /Покрытие себестоимости/i }).getAttribute("href")).toBe(
      "/app/finance/cost-coverage",
    );
  });
});
