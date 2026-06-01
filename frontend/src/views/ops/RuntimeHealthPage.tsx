import { useQuery } from "@tanstack/react-query";

import { api } from "../../state/http";
import { Card } from "../../ui/card";

export function RuntimeHealthPage() {
  const q = useQuery({
    queryKey: ["ops", "runtimeHealth"],
    queryFn: () => api.ops.runtimeHealth(),
  });

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Runtime health</div>
        <div className="text-sm text-slate-300">Read-only runtime probe (for operational visibility only).</div>
      </div>

      <Card className="p-5">
        {q.isLoading ? (
          <div className="text-sm text-slate-300">Loading…</div>
        ) : q.data ? (
          <pre className="overflow-auto text-[11px] text-slate-300">{JSON.stringify(q.data, null, 2)}</pre>
        ) : (
          <div className="text-sm text-slate-300">No data.</div>
        )}
      </Card>
    </div>
  );
}

