import type { ReportResponse } from "../../state/types-reports";

export type OnboardingProcessingPhase =
  | "pending"
  | "uploaded"
  | "processing"
  | "processed"
  | "failed";

export const PROCESSING_PHASE_LABELS: Record<OnboardingProcessingPhase, string> = {
  pending: "Отчёт принят",
  uploaded: "Файл загружен",
  processing: "Обрабатываем данные",
  processed: "Отчёт готов",
  failed: "Ошибка обработки",
};

export const POLL_INTERVAL_MS = 3_000;

export function isTerminalProcessingPhase(phase: OnboardingProcessingPhase): boolean {
  return phase === "processed" || phase === "failed";
}

export function deriveProcessingPhase(report: ReportResponse | null | undefined): OnboardingProcessingPhase {
  if (!report) return "pending";

  const status = (report.status ?? "").toLowerCase();
  const jobStatus = (report.job?.status ?? "").toLowerCase();

  if (status.includes("fail") || status.includes("dead")) return "failed";
  if (status.includes("processed") || status.includes("complete")) return "processed";
  if (status === "processing" || jobStatus === "processing") return "processing";
  if (status === "uploaded") return "uploaded";
  if (status === "pending") return "uploaded";

  return "pending";
}

export function pollIntervalForPhase(phase: OnboardingProcessingPhase): number | false {
  return isTerminalProcessingPhase(phase) ? false : POLL_INTERVAL_MS;
}

export function toneForProcessingPhase(phase: OnboardingProcessingPhase): "ok" | "warn" | "bad" | "info" {
  if (phase === "processed") return "ok";
  if (phase === "failed") return "bad";
  if (phase === "processing") return "info";
  return "warn";
}
