import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ProcessingStep } from "./ProcessingStep";

const reportsList = vi.fn();
const reportsGet = vi.fn();
const onRetryUpload = vi.fn();
const onOpenDashboard = vi.fn();

vi.mock("../../state/http", () => ({
  api: {
    reports: {
      list: (...args: unknown[]) => reportsList(...args),
      get: (...args: unknown[]) => reportsGet(...args),
    },
  },
}));

function renderStep() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ProcessingStep onRetryUpload={onRetryUpload} onOpenDashboard={onOpenDashboard} />
    </QueryClientProvider>,
  );
}

const baseReport = {
  id: "r-1",
  user_id: "u-1",
  marketplace: "wildberries",
  report_type: "finance",
  original_filename: "wb-report.xlsx",
  created_at: "2026-01-01T00:00:00Z",
};

describe("ProcessingStep", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("shows pending state when no report exists", async () => {
    reportsList.mockResolvedValue([]);
    renderStep();
    await waitFor(() => {
      expect(screen.getByTestId("onboarding-processing-status").textContent).toMatch(/Отчёт принят/);
    });
    expect(screen.queryByTestId("onboarding-open-dashboard-from-processing")).toBeNull();
    expect(screen.getByTestId("onboarding-open-later")).toBeTruthy();
  });

  it("shows processing state and open-later CTA", async () => {
    reportsList.mockResolvedValue([{ ...baseReport, status: "processing" }]);
    reportsGet.mockResolvedValue({
      ...baseReport,
      status: "processing",
      job: { id: "j-1", status: "processing", attempts: 1 },
    });

    renderStep();
    await waitFor(() => {
      expect(screen.getByTestId("onboarding-processing-status").textContent).toMatch(/Обрабатываем данные/);
    });
    expect(screen.getByTestId("onboarding-open-later")).toBeTruthy();
    expect(screen.getByTestId("onboarding-processing-filename").textContent).toMatch(/wb-report\.xlsx/);
  });

  it("shows processed state with open dashboard CTA", async () => {
    reportsList.mockResolvedValue([{ ...baseReport, status: "processed" }]);
    reportsGet.mockResolvedValue({ ...baseReport, status: "processed" });

    renderStep();
    await waitFor(() => {
      expect(screen.getByTestId("onboarding-processing-status").textContent).toMatch(/Отчёт готов/);
    });
    expect(screen.getByTestId("onboarding-open-dashboard-from-processing")).toBeTruthy();
    expect(screen.queryByTestId("onboarding-open-later")).toBeNull();
  });

  it("shows failed state with retry action", async () => {
    reportsList.mockResolvedValue([{ ...baseReport, status: "failed" }]);
    reportsGet.mockResolvedValue({
      ...baseReport,
      status: "failed",
      error_hint: "Проверьте формат файла.",
    });

    renderStep();
    await waitFor(() => {
      expect(screen.getByTestId("onboarding-processing-status").textContent).toMatch(/Ошибка обработки/);
      expect(screen.getByTestId("onboarding-processing-error").textContent).toMatch(/Проверьте формат файла/);
    });
    fireEvent.click(screen.getByTestId("onboarding-retry-upload"));
    expect(onRetryUpload).toHaveBeenCalledTimes(1);
  });

  it("open later CTA invokes dashboard handoff", async () => {
    reportsList.mockResolvedValue([{ ...baseReport, status: "processing" }]);
    reportsGet.mockResolvedValue({
      ...baseReport,
      status: "processing",
      job: { id: "j-1", status: "processing", attempts: 1 },
    });

    renderStep();
    fireEvent.click(await screen.findByTestId("onboarding-open-later"));
    expect(onOpenDashboard).toHaveBeenCalledTimes(1);
  });

  it("open dashboard CTA on processed invokes handoff", async () => {
    reportsList.mockResolvedValue([{ ...baseReport, status: "processed" }]);
    reportsGet.mockResolvedValue({ ...baseReport, status: "processed" });

    renderStep();
    fireEvent.click(await screen.findByTestId("onboarding-open-dashboard-from-processing"));
    expect(onOpenDashboard).toHaveBeenCalledTimes(1);
  });
});
