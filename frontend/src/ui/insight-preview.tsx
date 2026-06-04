/** Human-readable preview for AI insight JSON or recommendation API objects. */

const IMPACT_RU: Record<string, string> = {
  low: "низкий",
  moderate: "умеренный",
  high: "высокий",
};

const URGENCY_RU: Record<string, string> = {
  today: "сегодня",
  this_week: "на этой неделе",
  when_convenient: "когда удобно",
};

type InsightShape = {
  summary?: string;
  bullets?: string[];
  why?: string;
  expected_impact?: string;
  urgency?: string;
  recommended_actions?: string[];
  limitations?: string[];
  confidence_hint?: number;
  title?: string;
};

function asInsight(data: unknown): InsightShape | null {
  if (!data || typeof data !== "object") return null;
  const o = data as Record<string, unknown>;
  if (o.summary || o.bullets) return o as InsightShape;
  const plan = o.action_plan as Record<string, unknown> | undefined;
  const u = plan?.seller_usefulness as Record<string, unknown> | undefined;
  if (!o.title && !o.summary && !u) return null;
  return {
    title: String(o.title ?? ""),
    summary: String(o.summary ?? ""),
    why: String(u?.why_this_matters ?? plan?.why_this_matters ?? ""),
    expected_impact: String(u?.expected_business_impact ?? ""),
    urgency: String(u?.urgency ?? ""),
    recommended_actions: Array.isArray(plan?.recommended_actions)
      ? (plan!.recommended_actions as string[])
      : [],
    limitations: Array.isArray(o.limitations) ? (o.limitations as string[]) : [],
    confidence_hint: o.confidence_score != null ? Number(o.confidence_score) : undefined,
  };
}

export function InsightPreview(props: { data: unknown }) {
  const insight = asInsight(props.data);
  if (!insight) {
    return (
      <div className="text-xs text-ink-muted">Нет данных для отображения рекомендации.</div>
    );
  }

  const impact = insight.expected_impact
    ? IMPACT_RU[insight.expected_impact] ?? insight.expected_impact
    : null;
  const urgency = insight.urgency ? URGENCY_RU[insight.urgency] ?? insight.urgency : null;

  return (
    <div className="space-y-3 text-sm text-ink-secondary">
      {insight.title ? <div className="text-base font-semibold text-ink">{insight.title}</div> : null}
      {insight.summary ? <p className="leading-relaxed">{insight.summary}</p> : null}
      {(impact || urgency || insight.confidence_hint != null) && (
        <div className="flex flex-wrap gap-2 text-xs text-ink-muted">
          {impact ? <span>Эффект: {impact}</span> : null}
          {urgency ? <span>Срочность: {urgency}</span> : null}
          {insight.confidence_hint != null ? (
            <span>Уверенность: {Math.round(insight.confidence_hint * 100)}%</span>
          ) : null}
        </div>
      )}
      {insight.why ? (
        <div>
          <div className="text-xs font-medium text-ink-muted">Зачем это важно</div>
          <p className="mt-1 text-ink-secondary">{insight.why}</p>
        </div>
      ) : null}
      {insight.bullets && insight.bullets.length > 0 ? (
        <div>
          <div className="text-xs font-medium text-ink-muted">Наблюдения</div>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-ink-secondary">
            {insight.bullets.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {insight.recommended_actions && insight.recommended_actions.length > 0 ? (
        <div>
          <div className="text-xs font-medium text-ink-muted">Рекомендуемые действия</div>
          <ol className="mt-1 list-decimal space-y-1 pl-5 text-ink-secondary">
            {insight.recommended_actions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ol>
        </div>
      ) : null}
      {insight.limitations && insight.limitations.length > 0 ? (
        <div className="rounded-lg border border-amber-900/40 bg-amber-950/20 p-2 text-xs text-amber-100/90">
          <div className="font-medium">Ограничения</div>
          <ul className="mt-1 list-disc pl-4">
            {insight.limitations.map((l, i) => (
              <li key={i}>{l}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

/** Try to parse streamed raw text as JSON insight for preview. */
export function parseInsightJson(text: string): unknown | null {
  const trimmed = text.trim();
  if (!trimmed) return null;
  try {
    return JSON.parse(trimmed) as unknown;
  } catch {
    const start = trimmed.indexOf("{");
    const end = trimmed.lastIndexOf("}");
    if (start >= 0 && end > start) {
      try {
        return JSON.parse(trimmed.slice(start, end + 1)) as unknown;
      } catch {
        return null;
      }
    }
    return null;
  }
}
