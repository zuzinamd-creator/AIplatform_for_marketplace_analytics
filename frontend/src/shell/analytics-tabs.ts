export const ANALYTICS_HUB_ROUTE = "/app/analytics";
export const ANALYTICS_OVERVIEW_ROUTE = "/app/analytics";
export const ANALYTICS_WEEKLY_ROUTE = "/app/analytics/weekly";
export const ANALYTICS_ECONOMICS_ROUTE = "/app/analytics/economics";
export const ANALYTICS_COST_COVERAGE_ROUTE = "/app/analytics/cost-coverage";

export type AnalyticsTabId = "overview" | "weekly" | "economics" | "cost-coverage";

export type AnalyticsTab = {
  id: AnalyticsTabId;
  to: string;
  label: string;
  end?: boolean;
};

export const ANALYTICS_TABS: AnalyticsTab[] = [
  { id: "overview", to: ANALYTICS_OVERVIEW_ROUTE, label: "Обзор", end: true },
  { id: "weekly", to: ANALYTICS_WEEKLY_ROUTE, label: "Сравнение периодов" },
  { id: "economics", to: ANALYTICS_ECONOMICS_ROUTE, label: "Экономика SKU" },
  { id: "cost-coverage", to: ANALYTICS_COST_COVERAGE_ROUTE, label: "Покрытие себестоимости" },
];
