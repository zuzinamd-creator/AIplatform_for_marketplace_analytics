import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../../state/http";
import { Card } from "../../ui/card";
import { StatusBadge } from "../../ui/status-badge";
import { AiTrustNotice } from "../../ui/trust-banners";
import { priorityTierLabelRu } from "../../ui/seller-display";

const TYPES = [
  { id: "daily", label: "За день" },
  { id: "weekly", label: "За неделю" },
  { id: "anomaly", label: "Аномалии" },
] as const;

export function AiDigestPage() {
  const [params, setParams] = useSearchParams();
  const type = (params.get("type") as (typeof TYPES)[number]["id"]) || "daily";

  const digest = useQuery({
    queryKey: ["ai", "digest", type],
    queryFn: () => api.ai.digest(type),
  });

  const d = digest.data;

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-3">
        <div>
          <div className="text-2xl font-semibold">AI-сводка</div>
          <div className="text-sm text-ink-secondary">
            Краткие итоги по вашим рекомендациям — без автономных действий на маркетплейсе.
          </div>
        </div>
        <Link className="text-sm text-brand hover:underline" to="/app/ai/recommendations">
          Все рекомендации
        </Link>
      </div>

      <div className="flex flex-wrap gap-2">
        {TYPES.map((t) => (
          <button
            key={t.id}
            type="button"
            className={`rounded-lg border px-3 py-1.5 text-xs ${
              type === t.id
                ? "border-sky-700 bg-sky-950/50 text-brand"
                : "border-surface-subtle text-ink-muted hover:bg-surface-inset"
            }`}
            onClick={() => setParams({ type: t.id })}
          >
            {t.label}
          </button>
        ))}
      </div>

      {digest.isLoading ? (
        <Card className="p-5">Загрузка сводки…</Card>
      ) : d ? (
        <Card className="p-5 space-y-4">
          <div className="text-lg font-semibold">{d.headline}</div>
          <div className="text-xs text-ink0">
            Сформировано {new Date(d.generated_at).toLocaleString("ru-RU")} · {d.active_recommendation_count} шт.
          </div>
          <p className="text-xs text-ink-muted">{d.advisory_notice}</p>
          <div className="space-y-3">
            {d.sections.length === 0 ? (
              <div className="text-sm text-ink-muted">Нет разделов за этот период.</div>
            ) : (
              d.sections.map((s, i) => (
                <div key={i} className="rounded-lg border border-surface-subtle bg-surface-inset p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-sm font-medium text-ink-secondary">{s.title}</div>
                    <StatusBadge tone={s.priority === "high" ? "warn" : "info"}>
                      {priorityTierLabelRu(s.priority)}
                    </StatusBadge>
                  </div>
                  <p className="mt-2 text-xs text-ink-secondary">{s.body}</p>
                </div>
              ))
            )}
          </div>
        </Card>
      ) : (
        <Card className="p-5">Сводка недоступна.</Card>
      )}

      <AiTrustNotice />
    </div>
  );
}
