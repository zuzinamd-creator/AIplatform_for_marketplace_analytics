import { useQuery } from "@tanstack/react-query";

import { api } from "../../state/http";
import { Card } from "../../ui/card";
import { StatusBadge } from "../../ui/status-badge";

export function AiOperationalStatusPage() {
  const q = useQuery({
    queryKey: ["ai", "operationalStatus"],
    queryFn: () => api.ai.operationalStatus(),
  });

  const r = q.data as any;

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">AI Operational status</div>
        <div className="text-sm text-ink-secondary">Degraded mode banners and confidence indicators should be visible to sellers.</div>
      </div>

      {q.isLoading ? (
        <Card className="p-5">Loading…</Card>
      ) : r ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <Card className="p-5">
            <div className="text-xs text-ink-secondary">Overall score</div>
            <div className="mt-1 text-2xl font-semibold">{String(r.overall_score ?? "n/a")}</div>
            <div className="mt-3">
              {r.degraded_intelligence_mode ? (
                <StatusBadge tone="warn">Degraded mode</StatusBadge>
              ) : (
                <StatusBadge tone="ok">Normal</StatusBadge>
              )}
            </div>
          </Card>
          <Card className="p-5">
            <div className="text-xs text-ink-secondary">Success rate</div>
            <div className="mt-1 text-2xl font-semibold">{String(r.success_rate ?? "n/a")}</div>
            <div className="mt-1 text-xs text-ink-muted">Runs total: {String(r.runs_total ?? "n/a")}</div>
          </Card>
          <Card className="p-5">
            <div className="text-xs text-ink-secondary">Pending approvals</div>
            <div className="mt-1 text-2xl font-semibold">{String(r.pending_approvals ?? "n/a")}</div>
            <div className="mt-1 text-xs text-ink-muted">Avg confidence: {String(r.avg_confidence ?? "n/a")}</div>
          </Card>

          <Card className="p-5 md:col-span-3">
            <div className="text-sm font-semibold">Raw status payload</div>
            <pre className="mt-3 overflow-auto text-[11px] text-ink-secondary">{JSON.stringify(r, null, 2)}</pre>
          </Card>
        </div>
      ) : (
        <Card className="p-5">No data.</Card>
      )}
    </div>
  );
}

