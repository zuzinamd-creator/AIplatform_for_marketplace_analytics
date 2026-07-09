import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { cleanup, render, screen } from "@testing-library/react";

import { AuthProvider, RequirePlatformAdmin } from "./auth";
import { USER_ROLE_PLATFORM_ADMIN, USER_ROLE_SELLER } from "./userRoles";

vi.mock("./http", () => ({
  api: {
    auth: {
      me: vi.fn(),
    },
  },
  setAccessToken: vi.fn(),
}));

import { api } from "./http";

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

import type { UserResponse } from "./types";

function renderGuard(role: UserResponse["role"]) {
  localStorage.setItem("ma.accessToken", "token");
  vi.mocked(api.auth.me).mockResolvedValue(role === USER_ROLE_PLATFORM_ADMIN ? admin : seller);

  return render(
    <MemoryRouter initialEntries={["/app/ops/queue"]}>
      <AuthProvider>
        <Routes>
          <Route
            path="/app/ops/queue"
            element={
              <RequirePlatformAdmin>
                <div>ops-content</div>
              </RequirePlatformAdmin>
            }
          />
          <Route path="/app/dashboard" element={<div>dashboard</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("RequirePlatformAdmin", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("redirects seller to dashboard", async () => {
    renderGuard(USER_ROLE_SELLER);
    expect(await screen.findByText("dashboard")).toBeTruthy();
    expect(screen.queryByText("ops-content")).toBeNull();
  });

  it("allows platform_admin", async () => {
    renderGuard(USER_ROLE_PLATFORM_ADMIN);
    expect(await screen.findByText("ops-content")).toBeTruthy();
  });

  it("redirects seller from admin invites route", async () => {
    localStorage.setItem("ma.accessToken", "token");
    vi.mocked(api.auth.me).mockResolvedValue(seller);

    render(
      <MemoryRouter initialEntries={["/app/admin/invites"]}>
        <AuthProvider>
          <Routes>
            <Route
              path="/app/admin/invites"
              element={
                <RequirePlatformAdmin>
                  <div>admin-invites</div>
                </RequirePlatformAdmin>
              }
            />
            <Route path="/app/dashboard" element={<div>dashboard</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByText("dashboard")).toBeTruthy();
    expect(screen.queryByText("admin-invites")).toBeNull();
  });

  it("allows platform_admin on admin invites route", async () => {
    localStorage.setItem("ma.accessToken", "token");
    vi.mocked(api.auth.me).mockResolvedValue(admin);

    render(
      <MemoryRouter initialEntries={["/app/admin/invites"]}>
        <AuthProvider>
          <Routes>
            <Route
              path="/app/admin/invites"
              element={
                <RequirePlatformAdmin>
                  <div>admin-invites</div>
                </RequirePlatformAdmin>
              }
            />
            <Route path="/app/dashboard" element={<div>dashboard</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByText("admin-invites")).toBeTruthy();
  });

  it("redirects seller from admin users route", async () => {
    localStorage.setItem("ma.accessToken", "token");
    vi.mocked(api.auth.me).mockResolvedValue(seller);

    render(
      <MemoryRouter initialEntries={["/app/admin/users"]}>
        <AuthProvider>
          <Routes>
            <Route
              path="/app/admin/users"
              element={
                <RequirePlatformAdmin>
                  <div>admin-users</div>
                </RequirePlatformAdmin>
              }
            />
            <Route path="/app/dashboard" element={<div>dashboard</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByText("dashboard")).toBeTruthy();
    expect(screen.queryByText("admin-users")).toBeNull();
  });
});
