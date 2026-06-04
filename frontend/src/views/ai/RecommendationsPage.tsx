import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useMemo, useRef, useState } from "react";

import { api, formatApiError } from "../../state/http";
import { formatPct } from "../../utils/format";
import { t } from "../../i18n";
import { Card } from "../../ui/card";
import { StatusBadge } from "../../ui/status-badge";
import { Button } from "../../ui/button";
import { AiTrustNotice } from "../../ui/trust-banners";
import { InsightPreview, parseInsightJson } from "../../ui/insight-preview";
import { toast } from "../../ui/toast";

type InboxFilter = "inbox" | "saved" | "snoozed" | "completed" | "dismissed" | "all";

function priorityBand(score: number | string | null | undefined): "high" | "medium" | "low" {
  const n = Number(score ?? 0);
  if (n >= 70) return "high";
  if (n >= 40) return "medium";
  return "low";
}

export function RecommendationsPage() {
  const qc = useQueryClient();
  const [filter, setFilter] = useState<InboxFilter>("inbox");
  const [streamText, setStreamText] = useState("");
  const [streamStatus, setStreamStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [lastRun, setLastRun] = useState<Record<string, unknown> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const reports = useQuery({
    queryKey: ["reports", "list", 0, 5],
    queryFn: () => api.reports.list(0, 5),
  });

  const runAnalysis = useMutation({
    mutationFn: () =>
      api.ai.runIntelligence({
        workflow: "inventory_insight",
        prompt_id: "inventory.insight.v1",
        semantics_version: "1.0",
        report_id: (reports.data?.[0] as { id?: string } | undefined)?.id ?? null,
      }),
    onSuccess: async (res) => {
      setLastRun((res.recommendation as Record<string, unknown>) ?? { summary: res.summary });
      toast("Анализ готов", "Рекомендация добавлена во входящие.");
      await qc.invalidateQueries({ queryKey: ["ai", "recommendations"] });
      await qc.invalidateQueries({ queryKey: ["ai", "recommendationStats"] });
      await qc.invalidateQueries({ queryKey: ["ai", "usefulnessMetrics"] });
    },
    onError: (err) => toast("Ошибка анализа", formatApiError(err)),
  });

  const queryOpts = useMemo(() => {
    if (filter === "inbox") return { group: "inbox" };
    if (filter === "all") return {};
    return { seller_state: filter };
  }, [filter]);

  const q = useQuery({
    queryKey: ["ai", "recommendations", filter],
    queryFn: () => api.ai.recommendations(0, 50, queryOpts),
  });

  const stats = useQuery({
    queryKey: ["ai", "recommendationStats"],
    queryFn: () => api.ai.recommendationStats(),
  });

  const metrics = useQuery({
    queryKey: ["ai", "usefulnessMetrics"],
    queryFn: () => api.ai.usefulnessMetrics(),
  });

  const workflow = useMutation({
    mutationFn: (args: { id: string; action: string }) => api.ai.workflow(args.id, { action: args.action }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["ai", "recommendations"] });
      await qc.invalidateQueries({ queryKey: ["ai", "recommendationStats"] });
    },
  });

  const items = (q.data as any)?.items ?? [];

  const grouped = useMemo(() => {
    const buckets: Record<string, any[]> = { today: [], this_week: [], informational: [] };
    for (const r of items) {
      const tier =
        (r.lineage as { priority_tier?: string } | undefined)?.priority_tier ??
        (
          r.action_plan as
            | { seller_usefulness?: { prioritization?: { priority_tier?: string } } }
            | undefined
        )?.seller_usefulness?.prioritization?.priority_tier;
      if (tier === "today" || tier === "this_week" || tier === "informational") {
        buckets[tier].push(r);
      } else {
        const band = priorityBand(r.priority_score);
        if (band === "high") buckets.today.push(r);
        else if (band === "medium") buckets.this_week.push(r);
        else buckets.informational.push(r);
      }
    }
    return buckets;
  }, [items]);

  const apiBase = useMemo(() => {
    const base = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";
    const prefix = import.meta.env.VITE_API_PREFIX ?? "/api/v1";
    return `${base}${prefix}`;
  }, []);

  async function runStreamedInsight() {
    setStreamText("");
    setStreamStatus("running");
    const token = localStorage.getItem("ma.accessToken");
    const ac = new AbortController();
    abortRef.current = ac;
    try {
      const res = await fetch(`${apiBase}/ai/runs/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          workflow: "inventory_insight",
          prompt_id: "inventory.insight.v1",
          semantics_version: "1.0",
          report_id: null,
        }),
        signal: ac.signal,
      });
      if (!res.ok || !res.body) throw new Error(`stream failed: ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";
        for (const part of parts) {
          const line = part.split("\n").find((l) => l.startsWith("data:"));
          if (!line) continue;
          const jsonStr = line.replace(/^data:\s*/, "");
          const evt = JSON.parse(jsonStr) as any;
          if (evt.type === "delta") setStreamText((t) => t + String(evt.text ?? ""));
          if (evt.type === "error") throw new Error(String(evt.message ?? "unknown stream error"));
          if (evt.type === "final") setStreamStatus("done");
        }
      }
      if (streamStatus === "running") setStreamStatus("done");
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      setStreamStatus("error");
      setStreamText(
        (prev) =>
          prev + `\n\n${t("ai.stream_error_prefix")} ${e instanceof Error ? e.message : t("common.unknown_error")}`,
      );
    } finally {
      abortRef.current = null;
    }
  }

  const streamInsight = useMemo(() => parseInsightJson(streamText), [streamText]);

  const st = stats.data;
  const m = metrics.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-2xl font-semibold">{t("ai.inbox_title")}</div>
          <div className="text-sm text-ink-secondary">
            {t("ai.inbox_subtitle")}
          </div>
        </div>
        <div className="flex gap-3 text-sm">
          <Link className="text-brand hover:underline" to="/app/ai/today">
            {t("ai.todays_focus")}
          </Link>
          <Link className="text-brand hover:underline" to="/app/ai/digest?type=daily">
            {t("ai.daily_digest")}
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <Card className="p-3 text-xs">
          <div className="text-ink-muted">{t("ai.stats_open")}</div>
          <div className="text-lg font-semibold">{st?.total ?? "—"}</div>
        </Card>
        <Card className="p-3 text-xs">
          <div className="text-ink-muted">{t("ai.stats_conversion")}</div>
          <div className="text-lg font-semibold">
            {m?.action_conversion_rate != null ? formatPct(m.action_conversion_rate * 100) : "—"}
          </div>
        </Card>
        <Card className="p-3 text-xs">
          <div className="text-ink-muted">{t("ai.stats_completed")}</div>
          <div className="text-lg font-semibold">{m?.completed_count ?? st?.completed_count ?? "—"}</div>
        </Card>
        <Card className="p-3 text-xs">
          <div className="text-ink-muted">{t("ai.stats_ignored_7d")}</div>
          <div className="text-lg font-semibold">{st?.ignored_7d ?? m?.ignored_count ?? "—"}</div>
        </Card>
      </div>

      <div className="flex flex-wrap gap-2">
        {(["inbox", "saved", "snoozed", "completed", "dismissed", "all"] as InboxFilter[]).map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={`rounded-lg border px-3 py-1 text-xs capitalize ${
              filter === f
                ? "border-sky-700 bg-sky-950/50 text-brand"
                : "border-surface-subtle text-ink-muted"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      <Card className="p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold">Запуск анализа</div>
            <div className="mt-1 text-xs text-ink-muted">
              Создаёт рекомендацию во входящих (не сырой JSON). Используйте после загрузки отчётов и себестоимости.
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={runAnalysis.isPending || !(reports.data?.length ?? 0)}
              onClick={() => runAnalysis.mutate()}
            >
              {runAnalysis.isPending ? "Анализ…" : "Запустить анализ"}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void runStreamedInsight()}
              disabled={streamStatus === "running"}
            >
              {streamStatus === "running" ? "Поток…" : "Поток (отладка)"}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => abortRef.current?.abort()}
              disabled={streamStatus !== "running"}
            >
              Отмена
            </Button>
          </div>
        </div>
        {lastRun ? (
          <div className="mt-4 rounded-lg border border-brand-muted bg-surface-inset p-4">
            <InsightPreview data={lastRun} />
            {lastRun.id ? (
              <Link
                className="mt-3 inline-block text-xs text-brand hover:underline"
                to={`/app/ai/recommendations/${String(lastRun.id)}`}
              >
                Открыть карточку рекомендации →
              </Link>
            ) : null}
          </div>
        ) : null}
        {streamText ? (
          <div className="mt-4">
            {streamInsight ? (
              <InsightPreview data={streamInsight} />
            ) : (
              <pre className="max-h-32 overflow-auto rounded-lg border border-surface-subtle bg-surface-inset p-2 text-[11px] text-ink-muted">
                {streamText}
              </pre>
            )}
          </div>
        ) : null}
      </Card>

      {q.isLoading ? (
        <Card className="p-6">{t("common.loading")}</Card>
      ) : items.length === 0 ? (
        <Card className="p-10 text-center">
          <div className="text-sm font-medium">{t("ai.inbox_empty_title")}</div>
          <div className="mt-1 text-xs text-ink-muted">{t("ai.inbox_empty_hint")}</div>
        </Card>
      ) : filter === "inbox" ? (
        (
          [
            ["today", t("ai.band_today")],
            ["this_week", t("ai.band_this_week")],
            ["informational", t("ai.band_informational")],
          ] as const
        ).map(([band, label]) =>
          grouped[band].length > 0 ? (
            <div key={band} className="space-y-2">
              <div className="text-xs font-medium uppercase tracking-wide text-ink-muted">{label}</div>
              {grouped[band].map((r: any) => (
                <RecommendationRow key={String(r.id)} r={r} onWorkflow={(action) => workflow.mutate({ id: String(r.id), action })} />
              ))}
            </div>
          ) : null,
        )
      ) : (
        items.map((r: any) => (
          <RecommendationRow key={String(r.id)} r={r} onWorkflow={(action) => workflow.mutate({ id: String(r.id), action })} />
        ))
      )}

      <AiTrustNotice />
    </div>
  );
}

function RecommendationRow(props: { r: any; onWorkflow: (action: string) => void }) {
  const r = props.r;
  const plan = (r.action_plan ?? {}) as Record<string, unknown>;
  const u = (plan.seller_usefulness ?? {}) as Record<string, unknown>;
  const impactEst = plan.impact_estimate as Record<string, unknown> | undefined;
  const urgency = String(u.urgency ?? impactEst?.urgency ?? "");
  const tier =
    (r.lineage as { priority_tier?: string } | undefined)?.priority_tier ??
    (u.prioritization as { priority_tier?: string } | undefined)?.priority_tier;

  return (
    <Card className="p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <Link to={`/app/ai/recommendations/${r.id}`} className="min-w-0 flex-1 hover:underline">
          <div className="truncate text-sm font-medium text-ink">
            {String(r.title ?? r.summary ?? t("ai.rec_fallback_title"))}
          </div>
          <div className="mt-1 line-clamp-2 text-xs text-ink-muted">{String(u.why_this_matters ?? r.summary ?? "")}</div>
        </Link>
        <div className="flex flex-wrap gap-1">
          {tier ? <StatusBadge tone={tier === "today" ? "warn" : "info"}>{tier}</StatusBadge> : null}
          <StatusBadge tone="info">{String(r.confidence_score ?? "n/a")}</StatusBadge>
          {urgency ? <StatusBadge tone="warn">{urgency}</StatusBadge> : null}
          <StatusBadge tone="info">{String(r.seller_workflow_state ?? "active")}</StatusBadge>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button variant="ghost" size="sm" onClick={() => props.onWorkflow("save")}>
          {t("ai.action_save")}
        </Button>
        <Button variant="ghost" size="sm" onClick={() => props.onWorkflow("snooze")}>
          {t("ai.action_snooze_7d")}
        </Button>
        <Button variant="ghost" size="sm" onClick={() => props.onWorkflow("dismiss")}>
          {t("ai.action_dismiss")}
        </Button>
      </div>
    </Card>
  );
}
