import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { AuthProvider } from "../../state/auth";
import { LoginPage } from "./LoginPage";
import { USER_ROLE_SELLER } from "../../state/userRoles";

const navigateMock = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock("../../state/http", () => ({
  api: {
    auth: {
      login: vi.fn(),
      me: vi.fn(),
      registrationStatus: vi.fn().mockResolvedValue({ available: false }),
    },
  },
  formatApiError: (err: unknown) => String(err),
  setAccessToken: vi.fn(),
}));

import { api } from "../../state/http";

describe("LoginPage post-registration flow", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    navigateMock.mockReset();
    vi.mocked(api.auth.login).mockResolvedValue({ access_token: "token" });
    vi.mocked(api.auth.me).mockResolvedValue({
      id: "seller-1",
      email: "seller@example.com",
      role: USER_ROLE_SELLER,
      created_at: "2026-01-01T00:00:00Z",
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("redirects new seller to onboarding after first login", async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    const inputs = screen.getAllByRole("textbox");
    fireEvent.change(inputs[0]!, { target: { value: "seller@example.com" } });
    fireEvent.change(document.querySelector('input[type="password"]')!, { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: "Войти" }));

    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith("/app/onboarding", { replace: true });
    });
  });

  it("redirects seller with completed onboarding to analytics hub", async () => {
    localStorage.setItem("ma.onboardingDone", "true");

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    const inputs = screen.getAllByRole("textbox");
    fireEvent.change(inputs[0]!, { target: { value: "seller@example.com" } });
    fireEvent.change(document.querySelector('input[type="password"]')!, { target: { value: "password123" } });
    fireEvent.click(screen.getByRole("button", { name: "Войти" }));

    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith("/app/analytics", { replace: true });
    });
  });
});
