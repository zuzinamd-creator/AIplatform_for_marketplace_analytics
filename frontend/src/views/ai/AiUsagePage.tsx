import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "../../state/http";
import { formatMetric, formatUsd } from "../../utils/format";
import { Card } from "../../ui/card";
import { CollapsibleSection } from "../../ui/collapsible-section";
import { KpiCard } from "../../ui/kpi-card";
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
    <div className="page-shell">
      <div>
        <h1 className="page-title">Использование ИИ и провайдеры</h1>
        <p className="page-subtitle">Токены, лимиты расходов и состояние провайдеров (только просмотр).</p>
      </div>

      <div className="kpi-row">
        <KpiCard variant="hero" label="Расход сегодня" value={formatUsd(c?.daily_spend_usd)} sub={`Лимит: ${formatUsd(c?.daily_cap_usd)}`} />
        <KpiCard label="Остаток на сегодня" value={formatUsd(c?.daily_cap_remaining_usd)} />
        <KpiCard label="Оценка за месяц" value={formatUsd(p?.estimated_monthly_cost_usd)} />
        <KpiCard label="Токены (период)" value={formatMetric(u?.tokens_total)} />
      </div>

      <CollapsibleSection title="Статус провайдеров" subtitle="Primary, failover, circuit breaker" defaultOpen>
      <Card className="border-0 p-0 shadow-none">
        <div className="text-sm font-semibold">Provider status</div>
        {p ? (
          <div className="mt-3 space-y-2 text-xs text-ink-secondary">
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
              <div key={String(row.provider_id)} className="rounded border border-surface-subtle p-2">
                {String(row.provider_id)} — healthy={String(row.healthy)} failures=
                {String(row.consecutive_failures)}
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-2 text-sm text-ink-muted">Loading…</div>
        )}
      </Card>
      </CollapsibleSection>

      <CollapsibleSection title="Детализация расходов" subtitle="По workflow и дорогим запускам">
      <Card className="border-0 p-0 shadow-none">
        <div className="text-sm font-semibold">Cost breakdown</div>
        {c ? (
          <div className="mt-3 grid gap-4 md:grid-cols-2 text-xs text-ink-secondary">
            <div>
              <div className="font-medium text-ink-secondary">By workflow (agent)</div>
              <ul className="mt-1 list-inside list-disc">
                {(c.by_workflow ?? []).map((w, i) => (
                  <li key={i}>
                    {String((w as any).workflow)} — {(w as any).runs} runs, {formatUsd((w as any).cost_usd)}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <div className="font-medium text-ink-secondary">Expensive runs</div>
              <ul className="mt-1 list-inside list-disc">
                {(c.expensive_runs ?? []).map((r, i) => (
                  <li key={i}>
                    <Link className="text-brand hover:underline" to={`/app/ai/runs/${(r as any).run_id}`}>
                      {(r as any).run_id?.slice(0, 8)}
                    </Link>{" "}
                    — {formatUsd((r as any).cost_usd)}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : null}
      </Card>
      </CollapsibleSection>

      <AiTrustNotice />
    </div>
  );
}
