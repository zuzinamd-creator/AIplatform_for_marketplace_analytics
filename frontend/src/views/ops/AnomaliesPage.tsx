import { useQuery } from "@tanstack/react-query";

import { api } from "../../state/http";
import { Card } from "../../ui/card";

export function AnomaliesPage() {
  const q = useQuery({
    queryKey: ["ops", "anomalies", 0, 50],
    queryFn: () => api.ops.anomalies(0, 50),
  });

  const items = (q.data as any)?.items ?? [];

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Anomalies</div>
        <div className="text-sm text-slate-300">Operational anomalies are persisted outside ledger transactions.</div>
        <div className="mt-2 rounded-lg border border-slate-800/70 bg-slate-950/40 p-3 text-xs text-slate-300">
          <span className="font-medium text-slate-200">Investigation workflow:</span> identify anomaly → correlate with
          queue/rebuild state → review affected report(s) → run AI explainability prompt (if relevant).
        </div>
      </div>

      <Card className="p-5">
        {q.isLoading ? (
          <div className="text-sm text-slate-300">Loading…</div>
        ) : (
          <pre className="overflow-auto text-[11px] text-slate-300">{JSON.stringify(items, null, 2)}</pre>
        )}
      </Card>
    </div>
  );
}

