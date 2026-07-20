import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";
import { cleanup, render, screen } from "@testing-library/react";

import { AuthProvider, RequireAuth } from "./state/auth";
import { USER_ROLE_PLATFORM_ADMIN, USER_ROLE_SELLER } from "./state/userRoles";

vi.mock("./state/http", () => ({
  api: {
    auth: {
      me: vi.fn(),
    },
  },
  setAccessToken: vi.fn(),
}));

import { api } from "./state/http";

const seller = {
  id: "seller-1",
  email: "seller@example.com",
  role: USER_ROLE_SELLER,
  created_at: "2026-01-01T00:00:00Z",
};

const admin = {
  id: "admin-1",
  email: "admin@example.com",
  role: USER_ROLE_PLATFORM_ADMIN,
  created_at: "2026-01-01T00:00:00Z",
};

function renderLifecycleRoute(path: string, pageLabel: string, role: typeof USER_ROLE_SELLER | typeof USER_ROLE_PLATFORM_ADMIN) {
  localStorage.setItem("ma.accessToken", "token");
  vi.mocked(api.auth.me).mockResolvedValue(role === USER_ROLE_PLATFORM_ADMIN ? admin : seller);

  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <Routes>
          <Route
            path="/app"
            element={
              <RequireAuth>
                <Outlet />
              </RequireAuth>
            }
          >
            <Route path="onboarding" element={<div>{pageLabel}</div>} />
            <Route path="settings" element={<div>{pageLabel}</div>} />
            <Route path="support" element={<div>{pageLabel}</div>} />
            <Route path="analytics/weekly" element={<div>{pageLabel}</div>} />
          </Route>
          <Route path="/app/dashboard" element={<div>dashboard</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("seller lifecycle routes", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("allows seller to access onboarding under RequireAuth", async () => {
    renderLifecycleRoute("/app/onboarding", "onboarding-page", USER_ROLE_SELLER);
    expect(await screen.findByText("onboarding-page")).toBeTruthy();
    expect(screen.queryByText("dashboard")).toBeNull();
  });

  it("allows seller to access settings under RequireAuth", async () => {
    renderLifecycleRoute("/app/settings", "settings-page", USER_ROLE_SELLER);
    expect(await screen.findByText("settings-page")).toBeTruthy();
    expect(screen.queryByText("dashboard")).toBeNull();
  });

  it("allows seller to access support under RequireAuth", async () => {
    renderLifecycleRoute("/app/support", "support-page", USER_ROLE_SELLER);
    expect(await screen.findByText("support-page")).toBeTruthy();
    expect(screen.queryByText("dashboard")).toBeNull();
  });

  it("allows seller to access weekly analysis under RequireAuth", async () => {
    renderLifecycleRoute("/app/analytics/weekly", "weekly-analysis-page", USER_ROLE_SELLER);
    expect(await screen.findByText("weekly-analysis-page")).toBeTruthy();
    expect(screen.queryByText("dashboard")).toBeNull();
  });

  it("allows platform_admin to access onboarding", async () => {
    renderLifecycleRoute("/app/onboarding", "onboarding-page", USER_ROLE_PLATFORM_ADMIN);
    expect(await screen.findByText("onboarding-page")).toBeTruthy();
  });

  it("allows platform_admin to access settings", async () => {
    renderLifecycleRoute("/app/settings", "settings-page", USER_ROLE_PLATFORM_ADMIN);
    expect(await screen.findByText("settings-page")).toBeTruthy();
  });
});

describe("canonical route redirects", () => {
  afterEach(() => {
    cleanup();
  });

  it("redirects /app/ai/today to /app/today without cycles", async () => {
    render(
      <MemoryRouter initialEntries={["/app/ai/today"]}>
        <Routes>
          <Route path="/app">
            <Route path="ai/today" element={<Navigate to="/app/today" replace />} />
            <Route path="today" element={<div>today-page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("today-page")).toBeTruthy();
  });

  it("redirects /app/economics to /app/analytics/economics without cycles", async () => {
    render(
      <MemoryRouter initialEntries={["/app/economics"]}>
        <Routes>
          <Route path="/app">
            <Route path="economics" element={<Navigate to="/app/analytics/economics" replace />} />
            <Route path="analytics/economics" element={<div>economics-page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("economics-page")).toBeTruthy();
  });

  it("redirects /app/finance/cost-coverage to /app/analytics/cost-coverage without cycles", async () => {
    render(
      <MemoryRouter initialEntries={["/app/finance/cost-coverage"]}>
        <Routes>
          <Route path="/app">
            <Route
              path="finance/cost-coverage"
              element={<Navigate to="/app/analytics/cost-coverage" replace />}
            />
            <Route path="analytics/cost-coverage" element={<div>cost-coverage-page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("cost-coverage-page")).toBeTruthy();
  });

  it("redirects /app/finance/costs to /app/costs without cycles", async () => {
    render(
      <MemoryRouter initialEntries={["/app/finance/costs"]}>
        <Routes>
          <Route path="/app">
            <Route path="finance/costs" element={<Navigate to="/app/costs" replace />} />
            <Route path="costs" element={<div>costs-page</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("costs-page")).toBeTruthy();
  });

  it("redirects /app/analytics/overview to /app/analytics without cycles", async () => {
    render(
      <MemoryRouter initialEntries={["/app/analytics/overview"]}>
        <Routes>
          <Route path="/app/analytics">
            <Route path="overview" element={<Navigate to="/app/analytics" replace />} />
            <Route index element={<div>analytics-overview</div>} />
          </Route>
          <Route path="/app/analytics" element={<div>analytics-overview</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("analytics-overview")).toBeTruthy();
  });
});
