import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, waitFor } from "@testing-library/react";

import { TrustBanners } from "./trust-banners";
import { USER_ROLE_PLATFORM_ADMIN, USER_ROLE_SELLER } from "../state/userRoles";

const runtimeSummary = vi.fn();
const operationalStatus = vi.fn();
const reportsList = vi.fn();

vi.mock("../state/http", () => ({
  api: {
    ops: {
      runtimeSummary: (...args: unknown[]) => runtimeSummary(...args),
    },
    ai: {
      operationalStatus: (...args: unknown[]) => operationalStatus(...args),
    },
    reports: {
      list: (...args: unknown[]) => reportsList(...args),
    },
  },
}));

const useAuthMock = vi.fn();

vi.mock("../state/auth", () => ({
  useAuth: () => useAuthMock(),
}));

vi.mock("../state/settings", () => ({
  loadSettings: () => ({
    rebuild_alerts: true,
    ai_degraded_alerts: true,
    stale_data_alerts: true,
    product_mode: "mvp",
  }),
}));

function renderTrustBanners() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <TrustBanners />
    </QueryClientProvider>,
  );
}

describe("TrustBanners", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    runtimeSummary.mockResolvedValue({
      rebuild: { running: 1 },
      queue: {},
      health: {},
    });
    operationalStatus.mockResolvedValue({});
    reportsList.mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
  });

  it("does not poll ops runtimeSummary for seller", async () => {
    useAuthMock.mockReturnValue({
      user: { id: "s1", email: "seller@example.com", role: USER_ROLE_SELLER, created_at: "" },
    });

    renderTrustBanners();

    await waitFor(() => {
      expect(reportsList).toHaveBeenCalled();
    });

    expect(runtimeSummary).not.toHaveBeenCalled();
  });

  it("polls ops runtimeSummary for platform_admin", async () => {
    useAuthMock.mockReturnValue({
      user: { id: "a1", email: "admin@example.com", role: USER_ROLE_PLATFORM_ADMIN, created_at: "" },
    });

    renderTrustBanners();

    await waitFor(() => {
      expect(runtimeSummary).toHaveBeenCalled();
    });
  });
});
