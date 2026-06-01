import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { api } from "../../state/http";
import { Card } from "../../ui/card";

export function AiRunDetailPage() {
  const { runId } = useParams();
  const q = useQuery({
    queryKey: ["ai", "run", runId],
    queryFn: () => api.ai.run(runId!),
    enabled: Boolean(runId),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-3">
        <div>
          <div className="text-2xl font-semibold">AI Run detail</div>
          <div className="text-sm text-slate-300">Raw run object (useful for ops triage).</div>
        </div>
        <Link className="text-sm text-sky-300 hover:underline" to="/app/ai/runs">
          Back
        </Link>
      </div>

      {q.isLoading ? (
        <Card className="p-5">Loading…</Card>
      ) : q.data ? (
        <Card className="p-5">
          <pre className="overflow-auto text-[11px] text-slate-300">{JSON.stringify(q.data, null, 2)}</pre>
        </Card>
      ) : (
        <Card className="p-5">Not found.</Card>
      )}
    </div>
  );
}

