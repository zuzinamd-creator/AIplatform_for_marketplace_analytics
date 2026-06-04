import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "../../state/http";
import { Card } from "../../ui/card";
import { AiTrustNotice } from "../../ui/trust-banners";

function tierLabel(tier: string): string {
  if (tier === "today") return "Сделать сегодня";
  if (tier === "this_week") return "На этой неделе";
  return "Информация";
}

export function AiTodayPage() {
  const q = useQuery({
    queryKey: ["ai", "todaysFocus"],
    queryFn: () => api.ai.todaysFocus(),
  });
  const f = q.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-2xl font-semibold">Сегодня</div>
          <div className="text-sm text-ink-secondary">Ежедневный брифинг продавца: что требует внимания прямо сейчас.</div>
        </div>
        <Link className="text-sm text-brand hover:underline" to="/app/ai/recommendations">
          Все рекомендации →
        </Link>
      </div>

      <AiTrustNotice />

      {q.isLoading ? (
        <Card className="p-5">Загрузка брифинга…</Card>
      ) : !f ? (
        <Card className="p-5">Брифинг недоступен.</Card>
      ) : (
        <>
          <Card className="p-5">
            <div className="text-lg font-semibold">{f.headline}</div>
            <div className="mt-1 text-xs text-ink-muted">
              Сформировано {new Date(f.generated_at).toLocaleString()}
            </div>
            <p className="mt-3 text-sm text-ink-secondary">{f.advisory_notice}</p>
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
            <Card className="p-4">
              <div className="text-sm font-semibold text-rose-300">Критично сегодня</div>
              <ul className="mt-2 list-inside list-disc text-sm text-ink-secondary">
                {f.requires_attention_today.length === 0 ? (
                  <li className="text-ink0">Нет критичных задач на сегодня.</li>
                ) : (
                  f.requires_attention_today.map((t) => <li key={t}>{t}</li>)
                )}
              </ul>
            </Card>
            <Card className="p-4">
              <div className="text-sm font-semibold text-semantic-warn">Высокий риск</div>
              <ul className="mt-2 list-inside list-disc text-sm text-ink-secondary">
                {f.dangerous.length === 0 ? (
                  <li className="text-ink0">Нет критичных риск-флагов.</li>
                ) : (
                  f.dangerous.map((t) => <li key={t}>{t}</li>)
                )}
              </ul>
            </Card>
            <Card className="p-4">
              <div className="text-sm font-semibold text-emerald-300">Максимальный апсайд</div>
              <ul className="mt-2 list-inside list-disc text-sm text-ink-secondary">
                {f.highest_upside.map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
            </Card>
            <Card className="p-4">
              <div className="text-sm font-semibold text-ink-secondary">Можно позже</div>
              <ul className="mt-2 list-inside list-disc text-sm text-ink-secondary">
                {f.can_wait.slice(0, 6).map((t) => (
                  <li key={t}>{t}</li>
                ))}
              </ul>
            </Card>
          </div>

          <Card className="p-4">
            <div className="text-sm font-semibold">Топ-3 действия</div>
            <ol className="mt-2 space-y-2 text-sm">
              {f.top_actions.map((a, i) => (
                <li key={i} className="rounded border border-surface-subtle p-2">
                  <span className="text-ink-muted">{tierLabel(a.tier)} · </span>
                  {a.action}
                  {a.recommendation_id ? (
                    <Link
                      className="ml-2 text-brand hover:underline"
                      to={`/app/ai/recommendations/${a.recommendation_id}`}
                    >
                      Открыть
                    </Link>
                  ) : null}
                </li>
              ))}
            </ol>
          </Card>

          {f.critical_alerts.length > 0 ? (
            <Card className="border-rose-900/40 p-4">
              <div className="text-sm font-semibold text-rose-300">Критические алерты</div>
              <ul className="mt-2 space-y-2 text-sm">
                {f.critical_alerts.map((a, i) => (
                  <li key={i}>
                    <strong>{a.title}</strong>
                    <span className="text-ink-muted"> ({tierLabel(a.tier)})</span>
                    {a.why ? <div className="text-ink-muted">{a.why}</div> : null}
                  </li>
                ))}
              </ul>
            </Card>
          ) : null}

          {f.quick_wins.length > 0 ? (
            <Card className="p-4">
              <div className="text-sm font-semibold text-emerald-300">Быстрые победы</div>
              <ul className="mt-2 space-y-2 text-sm text-ink-secondary">
                {f.quick_wins.map((w, i) => (
                  <li key={i}>
                    {w.title} — {w.action} ({w.effort})
                  </li>
                ))}
              </ul>
            </Card>
          ) : null}

          <Card className="p-4">
            <div className="text-sm font-semibold">Очередь приоритетов</div>
            <div className="mt-3 space-y-2">
              {f.priority_queue.map((item) => (
                <Link
                  key={item.recommendation_id}
                  to={`/app/ai/recommendations/${item.recommendation_id}`}
                  className="block rounded border border-surface-subtle p-3 hover:border-brand-muted"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{item.title}</span>
                    <span className="text-xs text-ink-muted">
                      {tierLabel(item.priority_tier)} · {Math.round(item.recommendation_score)}
                    </span>
                  </div>
                  <div className="mt-1 line-clamp-2 text-xs text-ink-muted">{item.summary}</div>
                </Link>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
