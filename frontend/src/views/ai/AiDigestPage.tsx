import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../../state/http";
import { Card } from "../../ui/card";
import { StatusBadge } from "../../ui/status-badge";
import { AiTrustNotice } from "../../ui/trust-banners";

const TYPES = ["daily", "weekly", "anomaly"] as const;

export function AiDigestPage() {
  const [params, setParams] = useSearchParams();
  const type = (params.get("type") as (typeof TYPES)[number]) || "daily";

  const digest = useQuery({
    queryKey: ["ai", "digest", type],
    queryFn: () => api.ai.digest(type),
  });

  const d = digest.data;

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-3">
        <div>
          <div className="text-2xl font-semibold">AI Digest</div>
          <div className="text-sm text-slate-300">
            Summaries over your recommendations — not autonomous marketplace actions.
          </div>
        </div>
        <Link className="text-sm text-sky-300 hover:underline" to="/app/ai/recommendations">
          Inbox
        </Link>
      </div>

      <div className="flex flex-wrap gap-2">
        {TYPES.map((t) => (
          <button
            key={t}
            type="button"
            className={`rounded-lg border px-3 py-1.5 text-xs capitalize ${
              type === t
                ? "border-sky-700 bg-sky-950/50 text-sky-200"
                : "border-slate-800 text-slate-400 hover:bg-slate-900/50"
            }`}
            onClick={() => setParams({ type: t })}
          >
            {t}
          </button>
        ))}
      </div>

      {digest.isLoading ? (
        <Card className="p-5">Loading digest…</Card>
      ) : d ? (
        <Card className="p-5 space-y-4">
          <div className="text-lg font-semibold">{d.headline}</div>
          <div className="text-xs text-slate-500">
            Generated {new Date(d.generated_at).toLocaleString()} · {d.active_recommendation_count} item(s)
          </div>
          <p className="text-xs text-slate-400">{d.advisory_notice}</p>
          <div className="space-y-3">
            {d.sections.length === 0 ? (
              <div className="text-sm text-slate-400">No sections for this period.</div>
            ) : (
              d.sections.map((s, i) => (
                <div key={i} className="rounded-lg border border-slate-800/70 bg-slate-950/40 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-sm font-medium text-slate-200">{s.title}</div>
                    <StatusBadge tone={s.priority === "high" ? "warn" : "info"}>{s.priority}</StatusBadge>
                  </div>
                  <p className="mt-2 text-xs text-slate-300">{s.body}</p>
                </div>
              ))
            )}
          </div>
        </Card>
      ) : (
        <Card className="p-5">Digest unavailable.</Card>
      )}

      <AiTrustNotice />
    </div>
  );
}
