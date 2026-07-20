import { describe, expect, it } from "vitest";

import type { ReportResponse } from "../../state/types-reports";

import {
  deriveProcessingPhase,
  isTerminalProcessingPhase,
  POLL_INTERVAL_MS,
  pollIntervalForPhase,
  PROCESSING_PHASE_LABELS,
} from "./processing-step";

function report(overrides: Partial<ReportResponse> = {}): ReportResponse {
  return {
    id: "r-1",
    user_id: "u-1",
    marketplace: "wildberries",
    report_type: "finance",
    original_filename: "report.xlsx",
    status: "pending",
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("processing-step", () => {
  it("maps API statuses to seller-friendly phases", () => {
    expect(deriveProcessingPhase(null)).toBe("pending");
    expect(deriveProcessingPhase(report({ status: "pending" }))).toBe("uploaded");
    expect(deriveProcessingPhase(report({ status: "uploaded" }))).toBe("uploaded");
    expect(deriveProcessingPhase(report({ status: "processing" }))).toBe("processing");
    expect(
      deriveProcessingPhase(report({ status: "pending", job: { id: "j-1", status: "processing", attempts: 1 } })),
    ).toBe("processing");
    expect(deriveProcessingPhase(report({ status: "processed" }))).toBe("processed");
    expect(deriveProcessingPhase(report({ status: "failed" }))).toBe("failed");
  });

  it("exposes Russian labels for all phases", () => {
    expect(PROCESSING_PHASE_LABELS.pending).toBe("Отчёт принят");
    expect(PROCESSING_PHASE_LABELS.uploaded).toBe("Файл загружен");
    expect(PROCESSING_PHASE_LABELS.processing).toBe("Обрабатываем данные");
    expect(PROCESSING_PHASE_LABELS.processed).toBe("Отчёт готов");
    expect(PROCESSING_PHASE_LABELS.failed).toBe("Ошибка обработки");
  });

  it("stops polling only on processed or failed", () => {
    expect(isTerminalProcessingPhase("processed")).toBe(true);
    expect(isTerminalProcessingPhase("failed")).toBe(true);
    expect(isTerminalProcessingPhase("processing")).toBe(false);
    expect(isTerminalProcessingPhase("uploaded")).toBe(false);
    expect(isTerminalProcessingPhase("pending")).toBe(false);
    expect(pollIntervalForPhase("processing")).toBe(POLL_INTERVAL_MS);
    expect(pollIntervalForPhase("processed")).toBe(false);
    expect(pollIntervalForPhase("failed")).toBe(false);
  });
});
