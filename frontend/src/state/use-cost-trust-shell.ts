import { useQuery } from "@tanstack/react-query";

import { api } from "./http";
import { loadWorkspaceProfile } from "./onboarding";
import { loadPeriodSelection } from "./period";
import { useProfitTrust } from "./profit-trust";

/**
 * Shared integrity + cost coverage for AppShell global banner (Phase 9.6B-2).
 * Consumes backend contracts only — no client-side trust derivation.
 */
export function useCostTrustShellData() {
  const workspace = loadWorkspaceProfile();
  const marketplace = workspace.marketplace === "unknown" ? "wildberries" : workspace.marketplace;
  const { start, end } = loadPeriodSelection().range;

  const revenue = useQuery({
    queryKey: ["costTrustShell", "revenue", marketplace, start, end],
    queryFn: () => api.analytics.revenueSummary({ marketplace, start, end }),
    staleTime: 60_000,
  });

  const coverage = useQuery({
    queryKey: ["costTrustShell", "coverage", marketplace, start, end],
    queryFn: () => api.analytics.costCoverage({ marketplace, start, end, limit: 1 }),
    staleTime: 60_000,
  });

  return useProfitTrust(revenue.data?.integrity, coverage.data ?? null);
}
