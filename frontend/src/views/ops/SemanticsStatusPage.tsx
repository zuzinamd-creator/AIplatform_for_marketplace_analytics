import { useQuery } from "@tanstack/react-query";

import { api } from "../../state/http";
import { Card } from "../../ui/card";

export function SemanticsStatusPage() {
  const q = useQuery({
    queryKey: ["ops", "semanticsStatus"],
    queryFn: () => api.ops.semanticsStatus(),
  });

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Semantics status</div>
        <div className="text-sm text-ink-secondary">Visibility into semantics versions and rebuild requirements (read-only).</div>
      </div>

      <Card className="p-5">
        {q.isLoading ? (
          <div className="text-sm text-ink-secondary">Loading…</div>
        ) : q.data ? (
          <pre className="overflow-auto text-[11px] text-ink-secondary">{JSON.stringify(q.data, null, 2)}</pre>
        ) : (
          <div className="text-sm text-ink-secondary">No data.</div>
        )}
      </Card>
    </div>
  );
}

