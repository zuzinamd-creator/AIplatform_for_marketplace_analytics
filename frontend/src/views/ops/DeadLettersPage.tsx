import { useQuery } from "@tanstack/react-query";

import { api } from "../../state/http";
import { Card } from "../../ui/card";

export function DeadLettersPage() {
  const q = useQuery({
    queryKey: ["ops", "deadLetters", 0, 50],
    queryFn: () => api.ops.deadLetters(0, 50),
  });

  const items = (q.data as any)?.items ?? [];

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Dead letters</div>
        <div className="text-sm text-ink-secondary">Read-only list of jobs that reached terminal failure state.</div>
      </div>

      <Card className="p-5">
        {q.isLoading ? (
          <div className="text-sm text-ink-secondary">Loading…</div>
        ) : items.length > 0 ? (
          <pre className="overflow-auto text-[11px] text-ink-secondary">
            {JSON.stringify(items.slice(0, 50), null, 2)}
          </pre>
        ) : (
          <div className="text-sm text-ink-secondary">No dead letters.</div>
        )}
      </Card>
    </div>
  );
}

