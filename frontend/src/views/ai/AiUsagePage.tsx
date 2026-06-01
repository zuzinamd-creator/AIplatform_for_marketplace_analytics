import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "../../state/http";
import { Card } from "../../ui/card";
import { StatusBadge } from "../../ui/status-badge";
import { AiTrustNotice } from "../../ui/trust-banners";

export function AiUsagePage() {
  const costs = useQuery({ queryKey: ["ai", "costs"], queryFn: () => api.ai.costs() });
  const providers = useQuery({
    queryKey: ["ai", "providers"],
    queryFn: () => api.ai.providerStatus(),
  });
  const usage = useQuery({ queryKey: ["ai", "usage"], queryFn: () => api.ai.usage() });

  const c = costs.data;
  const p = providers.data;
  const u = usage.data;

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">AI Usage & Providers</div>
        <div className="text-sm text-slate-300">Operational visibility — tokens, cost caps, provider health.</div>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card className="p-3 text-xs">
          <div className="text-slate-400">Today spend</div>
          <div className="text-lg font-semibold">${c?.daily_spend_usd?.toFixed(4) ?? "—"}</div>
          <div className="text-slate-500">cap ${c?.daily_cap_usd ?? "—"}</div>
        </Card>
        <Card className="p-3 text-xs">
          <div className="text-slate-400">Remaining today</div>
          <div className="text-lg font-semibold">${c?.daily_cap_remaining_usd?.toFixed(4) ?? "—"}</div>
        </Card>
        <Card className="p-3 text-xs">
          <div className="text-slate-400">Est. monthly</div>
          <div className="text-lg font-semibold">${p?.estimated_monthly_cost_usd?.toFixed(2) ?? "—"}</div>
        </Card>
        <Card className="p-3 text-xs">
          <div className="text-slate-400">Tokens (period)</div>
          <div className="text-lg font-semibold">{u?.tokens_total ?? "—"}</div>
        </Card>
      </div>

      <Card className="p-5">
        <div className="text-sm font-semibold">Provider status</div>
        {p ? (
          <div className="mt-3 space-y-2 text-xs text-slate-300">
            <div className="flex flex-wrap gap-2">
              <StatusBadge tone="info">Primary: {p.primary_provider}</StatusBadge>
              {p.failover_provider ? (
                <StatusBadge tone="info">Failover: {p.failover_provider}</StatusBadge>
              ) : null}
              <StatusBadge tone={p.circuit_breaker_open ? "warn" : "ok"}>
                Circuit: {p.circuit_breaker_open ? "open" : "closed"}
              </StatusBadge>
              <StatusBadge tone="info">Prompt: {p.prompt_runtime_version}</StatusBadge>
            </div>
            {(p.providers ?? []).map((row: Record<string, unknown>) => (
              <div key={String(row.provider_id)} className="rounded border border-slate-800/60 p-2">
                {String(row.provider_id)} — healthy={String(row.healthy)} failures=
                {String(row.consecutive_failures)}
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-2 text-sm text-slate-400">Loading…</div>
        )}
      </Card>

      <Card className="p-5">
        <div className="text-sm font-semibold">Cost breakdown</div>
        {c ? (
          <div className="mt-3 grid gap-4 md:grid-cols-2 text-xs text-slate-300">
            <div>
              <div className="font-medium text-slate-200">By workflow (agent)</div>
              <ul className="mt-1 list-inside list-disc">
                {(c.by_workflow ?? []).map((w, i) => (
                  <li key={i}>
                    {String((w as any).workflow)} — {(w as any).runs} runs, ${Number((w as any).cost_usd).toFixed(4)}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <div className="font-medium text-slate-200">Expensive runs</div>
              <ul className="mt-1 list-inside list-disc">
                {(c.expensive_runs ?? []).map((r, i) => (
                  <li key={i}>
                    <Link className="text-sky-300 hover:underline" to={`/app/ai/runs/${(r as any).run_id}`}>
                      {(r as any).run_id?.slice(0, 8)}
                    </Link>{" "}
                    — ${Number((r as any).cost_usd).toFixed(4)}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : null}
      </Card>

      <AiTrustNotice />
    </div>
  );
}
