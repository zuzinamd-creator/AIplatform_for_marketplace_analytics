import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { ONBOARDING_STEPS, OnboardingPage } from "./OnboardingPage";

const navigateMock = vi.fn();
const setOnboardingDoneMock = vi.fn();
const saveWorkspaceProfileMock = vi.fn();
const reportsList = vi.fn();
const reportsGet = vi.fn();
const costsList = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock("../../state/onboarding", () => ({
  isOnboardingDone: () => false,
  loadWorkspaceProfile: () => ({ workspace_name: "Test shop", marketplace: "unknown" as const }),
  saveWorkspaceProfile: (...args: unknown[]) => saveWorkspaceProfileMock(...args),
  setOnboardingDone: (...args: unknown[]) => setOnboardingDoneMock(...args),
}));

vi.mock("../../state/http", () => ({
  api: {
    reports: {
      list: (...args: unknown[]) => reportsList(...args),
      get: (...args: unknown[]) => reportsGet(...args),
    },
    costs: {
      list: (...args: unknown[]) => costsList(...args),
    },
  },
}));

vi.mock("../../ui/toast", () => ({
  toast: vi.fn(),
}));

const processedReport = {
  id: "r-1",
  user_id: "u-1",
  marketplace: "wildberries",
  report_type: "finance",
  original_filename: "report.xlsx",
  status: "processed",
  created_at: "2026-01-01T00:00:00Z",
};

function mockReportsProcessed() {
  reportsList.mockResolvedValue([processedReport]);
  reportsGet.mockResolvedValue(processedReport);
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <OnboardingPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function advanceTo(stepId: (typeof ONBOARDING_STEPS)[number]["id"]) {
  const targetIdx = ONBOARDING_STEPS.findIndex((s) => s.id === stepId);
  expect(targetIdx).toBeGreaterThanOrEqual(0);

  for (let i = 0; i < targetIdx; i += 1) {
    const current = ONBOARDING_STEPS[i]!;
    if (current.id === "marketplace") {
      fireEvent.change(screen.getByRole("combobox"), { target: { value: "wildberries" } });
    }
    if (current.id === "workspace") {
      fireEvent.click(screen.getByTestId("onboarding-skip-workspace"));
    } else if (current.id === "cost_import") {
      fireEvent.click(screen.getByTestId("onboarding-skip-costs"));
    } else if (current.id === "processing") {
      mockReportsProcessed();
      await waitFor(() => {
        expect(screen.getByTestId("onboarding-next")).toBeTruthy();
      });
      fireEvent.click(screen.getByTestId("onboarding-next"));
    } else {
      fireEvent.click(screen.getByTestId("onboarding-next"));
    }
    expect(await screen.findByTestId(`onboarding-step-${ONBOARDING_STEPS[i + 1]!.id}`)).toBeTruthy();
  }
}

describe("OnboardingPage F2-C1", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockReportsProcessed();
    costsList.mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
  });

  it("uses F1.6 step order without forbidden steps", () => {
    expect(ONBOARDING_STEPS.map((s) => s.id)).toEqual([
      "value-intro",
      "workspace",
      "marketplace",
      "upload",
      "processing",
      "cost_import",
      "complete",
    ]);
    expect(ONBOARDING_STEPS.some((s) => s.id === "sku_mapping")).toBe(false);
    expect(ONBOARDING_STEPS.some((s) => s.id === "first_ai")).toBe(false);
    expect(ONBOARDING_STEPS.some((s) => s.id === "walkthrough")).toBe(false);
  });

  it("starts on value-intro step", async () => {
    renderPage();
    expect(await screen.findByTestId("onboarding-step-value-intro")).toBeTruthy();
    expect(screen.getByText(/Шаг 1 \/ 7/)).toBeTruthy();
  });

  it("allows skipping optional workspace step", async () => {
    renderPage();
    await screen.findByTestId("onboarding-step-value-intro");
    fireEvent.click(screen.getByTestId("onboarding-next"));
    expect(await screen.findByTestId("onboarding-step-workspace")).toBeTruthy();
    fireEvent.click(screen.getByTestId("onboarding-skip-workspace"));
    expect(await screen.findByTestId("onboarding-step-marketplace")).toBeTruthy();
  });

  it("blocks marketplace advance when marketplace is unknown", async () => {
    renderPage();
    await advanceTo("marketplace");
    fireEvent.click(screen.getByTestId("onboarding-next"));
    expect(await screen.findByTestId("onboarding-marketplace-error")).toBeTruthy();
    expect(screen.getByTestId("onboarding-step-marketplace")).toBeTruthy();
    expect(saveWorkspaceProfileMock).not.toHaveBeenCalled();
  });

  it("advances from marketplace after valid selection", async () => {
    renderPage();
    await advanceTo("marketplace");
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "wildberries" } });
    fireEvent.click(screen.getByTestId("onboarding-next"));
    expect(await screen.findByTestId("onboarding-step-upload")).toBeTruthy();
    expect(saveWorkspaceProfileMock).toHaveBeenCalledWith(
      expect.objectContaining({ marketplace: "wildberries" }),
    );
  });

  it("allows skipping optional costs step", async () => {
    renderPage();
    await advanceTo("cost_import");
    fireEvent.click(screen.getByTestId("onboarding-skip-costs"));
    expect(await screen.findByTestId("onboarding-step-complete")).toBeTruthy();
  });

  it("complete step finishes onboarding and navigates to analytics", async () => {
    renderPage();
    await advanceTo("complete");
    expect(screen.getByTestId("onboarding-open-dashboard")).toBeTruthy();
    expect(screen.queryByTestId("onboarding-next")).toBeNull();
    fireEvent.click(screen.getByTestId("onboarding-open-dashboard"));
    expect(setOnboardingDoneMock).toHaveBeenCalledWith(true);
    expect(navigateMock).toHaveBeenCalledWith("/app/analytics");
  });

  it("does not expose forbidden step content in the wizard", async () => {
    renderPage();
    await screen.findByTestId("onboarding-step-value-intro");
    expect(screen.queryByText(/inventory\.insight\.v1/i)).toBeNull();
    expect(screen.queryByText(/Сопоставление SKU/i)).toBeNull();
    expect(screen.queryByText(/Ежедневный ритм/i)).toBeNull();
  });

  it("links global skip to canonical analytics route", async () => {
    renderPage();
    await screen.findByTestId("onboarding-step-value-intro");
    expect(screen.getByRole("link", { name: /Пропустить и перейти к панели/i }).getAttribute("href")).toBe(
      "/app/analytics",
    );
  });
});

describe("OnboardingPage F2-C2 processing", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    costsList.mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
  });

  it("shows processing step after upload", async () => {
    reportsList.mockResolvedValue([]);
    renderPage();
    await advanceTo("upload");
    fireEvent.click(screen.getByTestId("onboarding-next"));
    expect(await screen.findByTestId("onboarding-step-processing")).toBeTruthy();
    expect(screen.getByTestId("onboarding-processing-panel")).toBeTruthy();
  });

  it("blocks Далее on processing until report is processed", async () => {
    reportsList.mockResolvedValue([
      { ...processedReport, status: "processing", job: { id: "j-1", status: "processing", attempts: 1 } },
    ]);
    reportsGet.mockResolvedValue({
      ...processedReport,
      status: "processing",
      job: { id: "j-1", status: "processing", attempts: 1 },
    });

    renderPage();
    await advanceTo("processing");
    expect(screen.queryByTestId("onboarding-next")).toBeNull();
    expect(screen.getByTestId("onboarding-open-later")).toBeTruthy();
  });

  it("processing open-later persists onboarding done and navigates", async () => {
    reportsList.mockResolvedValue([
      { ...processedReport, status: "processing", job: { id: "j-1", status: "processing", attempts: 1 } },
    ]);
    reportsGet.mockResolvedValue({
      ...processedReport,
      status: "processing",
      job: { id: "j-1", status: "processing", attempts: 1 },
    });

    renderPage();
    await advanceTo("processing");
    fireEvent.click(screen.getByTestId("onboarding-open-later"));
    expect(setOnboardingDoneMock).toHaveBeenCalledWith(true);
    expect(navigateMock).toHaveBeenCalledWith("/app/analytics");
  });

  it("failed processing returns user to upload step", async () => {
    reportsList.mockResolvedValue([{ ...processedReport, status: "failed" }]);
    reportsGet.mockResolvedValue({ ...processedReport, status: "failed", error_hint: "Неверный формат." });

    renderPage();
    await advanceTo("processing");
    fireEvent.click(screen.getByTestId("onboarding-retry-upload"));
    expect(await screen.findByTestId("onboarding-step-upload")).toBeTruthy();
  });

  it("allows Далее after processed and continues to cost_import", async () => {
    mockReportsProcessed();
    renderPage();
    await advanceTo("processing");
    await waitFor(() => {
      expect(screen.getByTestId("onboarding-processing-status").textContent).toMatch(/Отчёт готов/);
    });
    fireEvent.click(screen.getByTestId("onboarding-next"));
    expect(await screen.findByTestId("onboarding-step-cost_import")).toBeTruthy();
  });
});
