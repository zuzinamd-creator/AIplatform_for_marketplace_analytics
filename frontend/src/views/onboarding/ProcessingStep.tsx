import { Button } from "../../ui/button";
import { StatusBadge } from "../../ui/status-badge";

import {
  PROCESSING_PHASE_LABELS,
  toneForProcessingPhase,
  type OnboardingProcessingPhase,
} from "./processing-step";
import { useLatestReportPolling } from "./useLatestReportPolling";

type ProcessingStepProps = {
  onRetryUpload: () => void;
  onOpenDashboard: () => void;
};

function phaseHint(phase: OnboardingProcessingPhase, hasReport: boolean): string {
  if (!hasReport) {
    return "Загрузите отчёт на предыдущем шаге — после этого мы покажем прогресс обработки.";
  }
  if (phase === "pending" || phase === "uploaded") {
    return "Файл в системе. Обработка начнётся автоматически.";
  }
  if (phase === "processing") {
    return "Обычно это занимает несколько минут. Можно вернуться к панели позже.";
  }
  if (phase === "processed") {
    return "Данные готовы — продолжите настройку или откройте панель аналитики.";
  }
  return "Не удалось обработать файл. Попробуйте загрузить его снова.";
}

export function ProcessingStep(props: ProcessingStepProps) {
  const { report, phase, isLoading, hasReport } = useLatestReportPolling(true);
  const label = PROCESSING_PHASE_LABELS[phase];
  const showOpenLater = phase === "processing" || phase === "uploaded" || phase === "pending";
  const showOpenDashboard = phase === "processed";

  return (
    <div className="space-y-4 text-sm" data-testid="onboarding-processing-panel">
      <div className="flex flex-wrap items-center gap-2">
        <span data-testid="onboarding-processing-status">
          <StatusBadge tone={toneForProcessingPhase(phase)}>
            {isLoading && !report ? "Загрузка…" : label}
          </StatusBadge>
        </span>
        {report?.original_filename ? (
          <span className="text-xs text-ink-muted" data-testid="onboarding-processing-filename">
            {report.original_filename}
          </span>
        ) : null}
      </div>

      <div className="text-ink-secondary" data-testid="onboarding-processing-hint">
        {phaseHint(phase, hasReport)}
      </div>

      {phase === "failed" ? (
        <div className="space-y-3">
          <div className="text-xs text-semantic-danger" data-testid="onboarding-processing-error">
            {report?.error_hint || report?.error_message || "Попробуйте загрузить файл снова."}
          </div>
          <Button variant="secondary" onClick={props.onRetryUpload} data-testid="onboarding-retry-upload">
            Попробуйте загрузить файл снова
          </Button>
        </div>
      ) : null}

      {showOpenLater ? (
        <Button variant="secondary" onClick={props.onOpenDashboard} data-testid="onboarding-open-later">
          Открыть панель позже
        </Button>
      ) : null}

      {showOpenDashboard ? (
        <Button onClick={props.onOpenDashboard} data-testid="onboarding-open-dashboard-from-processing">
          Открыть панель
        </Button>
      ) : null}
    </div>
  );
}
