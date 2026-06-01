import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { api } from "../../state/http";
import { Card } from "../../ui/card";
import { StatusBadge } from "../../ui/status-badge";

function toneForStatus(status?: string) {
  const s = (status ?? "").toLowerCase();
  if (s.includes("fail") || s.includes("dead")) return "bad" as const;
  if (s.includes("process")) return "info" as const;
  if (s.includes("complete") || s.includes("processed")) return "ok" as const;
  return "warn" as const;
}

export function ReportDetailPage() {
  const { reportId } = useParams();
  const q = useQuery({
    queryKey: ["reports", "get", reportId],
    queryFn: () => api.reports.get(reportId!),
    enabled: Boolean(reportId),
  });

  const r = q.data;

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-3">
        <div>
          <div className="text-2xl font-semibold">Report detail</div>
          <div className="text-sm text-slate-300">Lifecycle is derived from `etl_jobs` and exposed via projection.</div>
        </div>
        <Link className="text-sm text-sky-300 hover:underline" to="/app/reports">
          Back to reports
        </Link>
      </div>

      {q.isLoading ? (
        <Card className="p-5">Loading…</Card>
      ) : r ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <Card className="p-5">
            <div className="text-sm font-semibold">File</div>
            <div className="mt-2 text-sm text-slate-200">{r.original_filename}</div>
            <div className="mt-1 font-mono text-[11px] text-slate-400">{r.file_checksum}</div>
            <div className="mt-3">
              <StatusBadge tone={toneForStatus(r.status)}>{r.status}</StatusBadge>
            </div>
            {r.error_message ? (
              <div className="mt-3 rounded-lg bg-rose-500/10 p-3 text-xs text-rose-200">
                {r.error_message}
              </div>
            ) : null}
          </Card>

          <Card className="p-5">
            <div className="text-sm font-semibold">Processing</div>
            <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="text-xs text-slate-400">Marketplace</div>
                <div className="mt-1">{r.marketplace}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Report type</div>
                <div className="mt-1">{r.report_type}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Created</div>
                <div className="mt-1">{r.created_at}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Processed</div>
                <div className="mt-1">{r.processed_at ?? "—"}</div>
              </div>
            </div>

            <div className="mt-4 rounded-lg border border-slate-800/70 bg-slate-950/40 p-3">
              <div className="text-xs font-medium text-slate-200">Job snapshot</div>
              <pre className="mt-2 overflow-auto text-[11px] text-slate-300">
                {JSON.stringify(r.job ?? null, null, 2)}
              </pre>
            </div>
          </Card>
        </div>
      ) : (
        <Card className="p-5">Not found.</Card>
      )}
    </div>
  );
}

