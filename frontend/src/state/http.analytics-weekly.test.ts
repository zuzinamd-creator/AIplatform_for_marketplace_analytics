import { describe, expect, it, vi } from "vitest";

const get = vi.fn();

vi.mock("axios", () => ({
  default: {
    create: () => ({
      get: (...args: unknown[]) => get(...args),
      post: vi.fn(),
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    }),
  },
}));

vi.mock("./session", () => ({
  handleUnauthorized: vi.fn(),
}));

describe("api.analytics weekly endpoints", () => {
  it("periodCompare calls correct path", async () => {
    get.mockResolvedValueOnce({ data: { data: { delta_revenue: "0" } } });
    const { api } = await import("./http");
    await api.analytics.periodCompare({
      marketplace: "wildberries",
      a_start: "2026-01-01",
      a_end: "2026-01-14",
      b_start: "2025-12-18",
      b_end: "2025-12-31",
    });
    expect(get).toHaveBeenCalledWith("/analytics/kpis/period-compare", {
      params: {
        marketplace: "wildberries",
        a_start: "2026-01-01",
        a_end: "2026-01-14",
        b_start: "2025-12-18",
        b_end: "2025-12-31",
      },
    });
  });

  it("abcAnalysis calls correct path", async () => {
    get.mockResolvedValueOnce({ data: { data: { buckets: [] } } });
    const { api } = await import("./http");
    await api.analytics.abcAnalysis({ marketplace: "wildberries", start: "2026-01-01", end: "2026-01-14" });
    expect(get).toHaveBeenCalledWith("/analytics/kpis/abc", {
      params: { marketplace: "wildberries", start: "2026-01-01", end: "2026-01-14" },
    });
  });

  it("inventoryRisk and warehouseAnalytics call correct paths", async () => {
    get.mockResolvedValue({ data: { data: {} } });
    const { api } = await import("./http");
    await api.analytics.inventoryRisk({ snapshot_date: "2026-01-14" });
    await api.analytics.warehouseAnalytics({ snapshot_date: "2026-01-14" });
    expect(get).toHaveBeenCalledWith("/analytics/kpis/inventory-risk", {
      params: { snapshot_date: "2026-01-14" },
    });
    expect(get).toHaveBeenCalledWith("/analytics/kpis/warehouses", {
      params: { snapshot_date: "2026-01-14" },
    });
  });
});
