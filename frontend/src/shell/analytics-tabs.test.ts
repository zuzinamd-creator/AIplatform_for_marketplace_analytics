import { describe, expect, it } from "vitest";

import {
  ANALYTICS_COST_COVERAGE_ROUTE,
  ANALYTICS_ECONOMICS_ROUTE,
  ANALYTICS_HUB_ROUTE,
  ANALYTICS_TABS,
  ANALYTICS_WEEKLY_ROUTE,
} from "./analytics-tabs";

describe("analytics-tabs", () => {
  it("defines four hub tabs with stable route aliases", () => {
    expect(ANALYTICS_TABS.map((t) => t.label)).toEqual([
      "Обзор",
      "Сравнение периодов",
      "Экономика SKU",
      "Покрытие себестоимости",
    ]);
    expect(ANALYTICS_HUB_ROUTE).toBe("/app/analytics");
    expect(ANALYTICS_WEEKLY_ROUTE).toBe("/app/analytics/weekly");
    expect(ANALYTICS_ECONOMICS_ROUTE).toBe("/app/analytics/economics");
    expect(ANALYTICS_COST_COVERAGE_ROUTE).toBe("/app/analytics/cost-coverage");
  });
});
