import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "../../state/http";
import { Card } from "../../ui/card";

export function AiRunsPage() {
  const q = useQuery({
    queryKey: ["ai", "runs", 0, 50],
    queryFn: () => api.ai.runs(0, 50),
  });

  const items = (q.data as any)?.items ?? [];

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">AI Runs</div>
        <div className="text-sm text-slate-300">Governed run history (read-only).</div>
      </div>

      <Card className="overflow-hidden">
        <div className="grid grid-cols-12 border-b border-slate-800/70 bg-slate-950/40 px-4 py-3 text-xs text-slate-300">
          <div className="col-span-4">Run ID</div>
          <div className="col-span-3">Workflow</div>
          <div className="col-span-3">Status</div>
          <div className="col-span-2">Created</div>
        </div>

        {q.isLoading ? (
          <div className="px-4 py-6 text-sm text-slate-300">Loading…</div>
        ) : items.length > 0 ? (
          items.map((r: any) => (
            <Link
              key={String(r.id)}
              to={`/app/ai/runs/${r.id}`}
              className="grid grid-cols-12 border-b border-slate-800/40 px-4 py-3 text-sm hover:bg-slate-900/40"
            >
              <div className="col-span-4 truncate font-mono text-[12px]">{String(r.id)}</div>
              <div className="col-span-3 truncate">{String(r.workflow ?? "—")}</div>
              <div className="col-span-3 truncate">{String(r.status ?? r.state ?? "—")}</div>
              <div className="col-span-2 truncate text-slate-300">{String(r.created_at ?? "—")}</div>
            </Link>
          ))
        ) : (
          <div className="px-4 py-10 text-center">
            <div className="text-sm font-medium">No AI runs yet</div>
            <div className="mt-1 text-xs text-slate-400">Once you run intelligence workflows, they’ll show up here.</div>
          </div>
        )}
      </Card>
    </div>
  );
}

