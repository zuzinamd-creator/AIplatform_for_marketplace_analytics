import { useQuery } from "@tanstack/react-query";

import { api } from "../../state/http";

import {
  deriveProcessingPhase,
  pollIntervalForPhase,
  type OnboardingProcessingPhase,
} from "./processing-step";

export function useLatestReportPolling(enabled: boolean) {
  const listQuery = useQuery({
    queryKey: ["reports", "list", 0, 1],
    queryFn: () => api.reports.list(0, 1),
    enabled,
  });

  const latestReport = listQuery.data?.[0];
  const reportId = latestReport?.id;

  const detailQuery = useQuery({
    queryKey: ["reports", "get", reportId],
    queryFn: () => api.reports.get(reportId!),
    enabled: enabled && Boolean(reportId),
    refetchInterval: (query) => {
      const phase = deriveProcessingPhase(query.state.data);
      return pollIntervalForPhase(phase);
    },
  });

  const report = detailQuery.data ?? latestReport;
  const phase: OnboardingProcessingPhase = deriveProcessingPhase(report);
  const isLoading = listQuery.isLoading || (Boolean(reportId) && detailQuery.isLoading);

  return {
    report,
    reportId,
    phase,
    isLoading,
    hasReport: Boolean(reportId),
  };
}
