import { useQuery } from "@tanstack/react-query";

import { api } from "../../state/http";
import { Card } from "../../ui/card";
import { StatusBadge } from "../../ui/status-badge";

export function QueuePage() {
  const q = useQuery({
    queryKey: ["ops", "queue", 0, 50],
    queryFn: () => api.ops.queue(0, 50),
  });

  const items = (q.data as any)?.items ?? [];
  const counts = (q.data as any)?.status_counts ?? {};

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Queue status</div>
        <div className="text-sm text-slate-300">Read-only view of tenant job queue (claim/retry/visibility).</div>
      </div>

      <div className="flex flex-wrap gap-2">
        {Object.keys(counts).length > 0 ? (
          Object.entries(counts).map(([k, v]) => (
            <StatusBadge key={k} tone="info">
              {k}: {String(v)}
            </StatusBadge>
          ))
        ) : (
          <StatusBadge tone="warn">No status_counts</StatusBadge>
        )}
      </div>

      <Card className="p-5">
        {q.isLoading ? (
          <div className="text-sm text-slate-300">Loading…</div>
        ) : (
          <pre className="overflow-auto text-[11px] text-slate-300">
            {JSON.stringify(items.slice(0, 50), null, 2)}
          </pre>
        )}
      </Card>
    </div>
  );
}

