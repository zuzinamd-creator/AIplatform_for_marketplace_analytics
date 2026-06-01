import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../../state/http";
import { Card } from "../../ui/card";
import { Button } from "../../ui/button";
import { Label, Textarea } from "../../ui/field";
import { StatusBadge } from "../../ui/status-badge";
import { AiTrustNotice } from "../../ui/trust-banners";
import { AiTrustPanel } from "../../ui/ai-trust-panel";
import { toast } from "../../ui/toast";
import { trackUsage } from "../../state/usage";

export function RecommendationDetailPage() {
  const { recommendationId } = useParams();
  const qc = useQueryClient();
  const [overrideReason, setOverrideReason] = useState("");
  const [rating, setRating] = useState<number>(5);
  const [followUp, setFollowUp] = useState("");
  const [conversation, setConversation] = useState<Array<{ q: string; a: string }>>([]);
  const [note, setNote] = useState("");
  const [reminderDate, setReminderDate] = useState<string>("");

  const rec = useQuery({
    queryKey: ["ai", "recommendation", recommendationId],
    queryFn: () => api.ai.recommendation(recommendationId!),
    enabled: Boolean(recommendationId),
  });

  const explain = useQuery({
    queryKey: ["ai", "explainability", recommendationId],
    queryFn: () => api.ai.explainability(recommendationId!),
    enabled: Boolean(recommendationId),
  });

  const workflow = useMutation({
    mutationFn: (action: string) => api.ai.workflow(recommendationId!, { action }),
    onSuccess: async () => {
      toast("Готово", "Действие сохранено.");
      await qc.invalidateQueries({ queryKey: ["ai", "recommendation", recommendationId] });
      await qc.invalidateQueries({ queryKey: ["ai", "recommendations"] });
    },
    onError: (err) => toast("Не удалось", err instanceof Error ? err.message : "Ошибка"),
  });

  const createEvent = useMutation({
    mutationFn: (body: { event_type: string; note?: string; reminder_at?: string | null }) =>
      api.workflow.createEvent({
        recommendation_id: recommendationId!,
        event_type: body.event_type,
        note: body.note,
        reminder_at: body.reminder_at ?? null,
      }),
    onSuccess: async () => {
      toast("Готово", "Сохранено в истории.");
      await qc.invalidateQueries({ queryKey: ["workflow", "history", recommendationId] });
    },
    onError: (err) => toast("Не удалось", err instanceof Error ? err.message : "Ошибка"),
  });

  const history = useQuery({
    queryKey: ["workflow", "history", recommendationId],
    queryFn: () => api.workflow.history({ recommendation_id: recommendationId!, limit: 50 }),
    enabled: Boolean(recommendationId),
  });

  const ask = useMutation({
    mutationFn: (question: string) => api.ai.ask(recommendationId!, question),
    onSuccess: (data) => {
      setConversation((c) => [...c, { q: data.question, a: data.answer }]);
      setFollowUp("");
    },
    onError: (err) => toast("Не удалось спросить", err instanceof Error ? err.message : "Неизвестная ошибка"),
  });

  const feedback = useMutation({
    mutationFn: async (body: { helpful: boolean; feedback_type: string }) =>
      api.ai.feedback(recommendationId!, {
        ...body,
        rating,
        override_reason: overrideReason,
      }),
    onSuccess: async () => {
      trackUsage("recommendation_feedback", { type: "recorded" });
      toast("Отзыв сохранён", "Спасибо — это повышает релевантность рекомендаций.");
      await qc.invalidateQueries({ queryKey: ["ai", "recommendations"] });
    },
    onError: (err) => toast("Не удалось сохранить отзыв", err instanceof Error ? err.message : "Неизвестная ошибка"),
  });

  const r = rec.data as any;
  const e = explain.data as any;
  const plan = (r?.action_plan ?? {}) as any;
  const u = (plan.seller_usefulness ?? {}) as Record<string, unknown>;
  const why = String(u.why_this_matters ?? plan.why_this_matters ?? "");
  const action = String(u.concrete_next_action ?? plan.recommended_action ?? "");
  const impact = String(u.expected_business_impact ?? "");
  const upside = String(u.estimated_upside ?? "");
  const downside = String(u.estimated_downside ?? "");
  const urgency = String(u.urgency ?? "");
  const confExplain = String(u.confidence_explanation ?? "");
  const fingerprint = String((r?.lineage ?? {})?.fingerprint ?? "");

  const nodes = (e?.evidence_graph?.nodes ?? []) as Array<any>;
  const edges = (e?.evidence_graph?.edges ?? []) as Array<any>;
  const domainInsights = (e?.reasoning_trace?.domain_insights ?? []) as Array<{
    insight_id?: string;
    analyst_id?: string;
    analyst_label?: string;
    statement?: string;
    confidence?: string | number;
    severity?: string;
    priority_rank?: number;
    evidence_refs?: string[];
    recommended_actions?: string[];
    reasoning_summary?: string;
  }>;

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-3">
        <div>
          <div className="text-2xl font-semibold">Рекомендация</div>
          <div className="text-sm text-slate-300">Доверие к данным, ограничения и история действий продавца.</div>
        </div>
        <Link className="text-sm text-sky-300 hover:underline" to="/app/ai/recommendations">
          Назад
        </Link>
      </div>

      {rec.isLoading ? (
        <Card className="p-5">Загрузка…</Card>
      ) : r ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <Card className="p-5">
            <div className="text-sm font-semibold">Суть</div>
            <div className="mt-2 text-sm text-slate-200">{String(r.summary ?? "")}</div>

            <div className="mt-4 flex flex-wrap gap-2">
              <StatusBadge tone="info">Уверенность: {String(r.confidence_score ?? r.confidence ?? "—")}</StatusBadge>
              <StatusBadge tone="info">Риск: {String(r.risk_class ?? "—")}</StatusBadge>
              {r.requires_human_approval ? (
                <StatusBadge tone="warn">Требует подтверждения</StatusBadge>
              ) : (
                <StatusBadge tone="ok">Авто</StatusBadge>
              )}
            </div>

            <div className="mt-4 space-y-3 text-xs text-slate-300">
              {urgency ? (
                <div>
                  <span className="font-medium text-slate-200">Срочность: </span>
                  {urgency.replace(/_/g, " ")}
                </div>
              ) : null}
              <div>
                <div className="font-medium text-slate-200">Почему это важно</div>
                <p className="mt-1">{why || "Перед действием проверьте KPI и качество данных."}</p>
              </div>
              {impact ? (
                <div>
                  <div className="font-medium text-slate-200">Ожидаемый эффект</div>
                  <p className="mt-1">{impact}</p>
                </div>
              ) : null}
              {(upside || downside) && (
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {upside ? (
                    <div className="rounded border border-emerald-900/40 bg-emerald-950/20 p-2">
                      <div className="text-emerald-200/90">Потенциальный плюс</div>
                      <div className="mt-1">{upside}</div>
                    </div>
                  ) : null}
                  {downside ? (
                    <div className="rounded border border-rose-900/40 bg-rose-950/20 p-2">
                      <div className="text-rose-200/90">Риск, если игнорировать</div>
                      <div className="mt-1">{downside}</div>
                    </div>
                  ) : null}
                </div>
              )}
              <div>
                <div className="font-medium text-slate-200">Что сделать</div>
                <p className="mt-1 text-slate-200">{action}</p>
              </div>
              {confExplain ? (
                <div>
                  <div className="font-medium text-slate-200">Почему такая уверенность</div>
                  <p className="mt-1">{confExplain}</p>
                </div>
              ) : null}
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="secondary" size="sm" onClick={() => workflow.mutate("complete")} disabled={workflow.isPending}>
                Сделано
              </Button>
              <Button variant="ghost" size="sm" onClick={() => workflow.mutate("save")} disabled={workflow.isPending}>
                В избранное
              </Button>
              <Button variant="ghost" size="sm" onClick={() => workflow.mutate("snooze")} disabled={workflow.isPending}>
                Вернуться через 7 дней
              </Button>
              <Button variant="ghost" size="sm" onClick={() => workflow.mutate("dismiss")} disabled={workflow.isPending}>
                Скрыть
              </Button>
              <Button variant="ghost" size="sm" onClick={() => workflow.mutate("done_today")} disabled={workflow.isPending}>
                Сделать сегодня
              </Button>
              <Button variant="ghost" size="sm" onClick={() => workflow.mutate("waiting_for_data")} disabled={workflow.isPending}>
                Жду данные
              </Button>
            </div>

            <div className="mt-6 rounded-lg border border-slate-800/70 bg-slate-950/40 p-3">
              <div className="text-sm font-semibold">Заметка продавца</div>
              <div className="mt-2 space-y-2">
                <Textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Коротко: что и почему нужно сделать…" />
                <div className="flex flex-wrap items-end gap-2">
                  <div className="min-w-[240px]">
                    <Label>Напомнить</Label>
                    <input
                      className="mt-1 h-9 w-full rounded-md border border-slate-800 bg-slate-950/40 px-2 text-sm"
                      type="datetime-local"
                      value={reminderDate}
                      onChange={(e) => setReminderDate(e.target.value)}
                    />
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() =>
                      createEvent.mutate({
                        event_type: "note",
                        note,
                        reminder_at: reminderDate ? new Date(reminderDate).toISOString() : null,
                      })
                    }
                    disabled={createEvent.isPending || (!note.trim() && !reminderDate)}
                  >
                    Сохранить
                  </Button>
                </div>
              </div>
            </div>

            <div className="mt-5 rounded-lg border border-slate-800/70 bg-slate-950/40 p-3">
              <div className="text-xs font-medium text-slate-200">Задать вопрос по рекомендации</div>
              <p className="mt-1 text-[11px] text-slate-500">
                Ответы формируются детерминированно из сохранённых доказательств — без автономных действий на маркетплейсе.
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {["why", "impact", "action", "confidence", "evidence", "limitations"].map((chip) => (
                  <button
                    key={chip}
                    type="button"
                    className="rounded border border-slate-700 px-2 py-0.5 text-[11px] text-slate-300 hover:bg-slate-800"
                    onClick={() => ask.mutate(chip)}
                  >
                    {chip}
                  </button>
                ))}
              </div>
              <div className="mt-2 flex gap-2">
                <input
                  className="h-9 flex-1 rounded-lg border border-slate-800 bg-slate-950/40 px-3 text-sm"
                  value={followUp}
                  onChange={(ev) => setFollowUp(ev.target.value)}
                  placeholder="Или напишите вопрос…"
                />
                <Button variant="secondary" size="sm" onClick={() => followUp && ask.mutate(followUp)} disabled={ask.isPending}>
                  Спросить
                </Button>
              </div>
              {conversation.length > 0 ? (
                <div className="mt-3 max-h-48 space-y-2 overflow-auto">
                  {conversation.map((turn, i) => (
                    <div key={i} className="rounded bg-slate-900/50 p-2 text-[11px]">
                      <div className="text-slate-500">Вопрос: {turn.q}</div>
                      <div className="mt-1 text-slate-200">{turn.a}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
            {fingerprint ? (
              <div className="mt-2 text-[11px] text-slate-500">
                Идентификатор: <span className="text-slate-400">{fingerprint.slice(0, 16)}</span>
              </div>
            ) : null}

            <div className="mt-5 space-y-2">
              <div className="text-xs font-medium text-slate-200">Оценка полезности</div>
              <div className="flex flex-wrap items-center gap-2">
                <div className="text-xs text-slate-400">Насколько это полезно?</div>
                <select
                  className="h-9 rounded-lg border border-slate-800 bg-slate-950/40 px-3 text-sm text-slate-50"
                  value={rating}
                  onChange={(e) => setRating(Number(e.target.value))}
                >
                  <option value={1}>1 — не полезно</option>
                  <option value={2}>2</option>
                  <option value={3}>3</option>
                  <option value={4}>4</option>
                  <option value={5}>5 — очень полезно</option>
                </select>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="secondary"
                  onClick={() => feedback.mutate({ helpful: true, feedback_type: "accept" })}
                  disabled={feedback.isPending}
                >
                  Принять
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => feedback.mutate({ helpful: false, feedback_type: "reject" })}
                  disabled={feedback.isPending}
                >
                  Отклонить
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => feedback.mutate({ helpful: true, feedback_type: "note" })}
                  disabled={feedback.isPending}
                >
                  Добавить заметку
                </Button>
              </div>
              <div className="space-y-1.5">
                <Label>Причина (необязательно)</Label>
                <Textarea
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  rows={4}
                  placeholder="Почему вы приняли/отклонили (ограничения по цене, склад, сроки кампании и т.п.)"
                />
              </div>
            </div>
          </Card>

          <Card className="p-5">
            <div className="text-sm font-semibold">Доверие и доказательства</div>
            {explain.isLoading ? (
              <div className="mt-3 text-sm text-slate-300">Загрузка объяснимости…</div>
            ) : e ? (
              <>
                <div className="mt-3">
                  <AiTrustPanel trust={e.trust_context} />
                </div>
                <div className="mt-2 text-xs text-slate-300">{String(e.confidence_rationale ?? "")}</div>
                <div className="mt-4 rounded-lg border border-slate-800/70 bg-slate-950/40 p-3">
                  <div className="text-sm font-semibold">Почему AI может ошибаться</div>
                  <div className="mt-2 text-sm text-slate-200">
                    {String(
                      e?.trust_context?.confidence_explanation ??
                        confExplain ??
                        "ИИ — advisory. Он опирается на загруженные отчёты и governed метрики. При неполных данных уверенность снижается.",
                    )}
                  </div>
                  {Array.isArray(e?.trust_context?.limitations) && e.trust_context.limitations.length ? (
                    <ul className="mt-3 space-y-1 text-xs text-slate-300">
                      {e.trust_context.limitations.slice(0, 10).map((l: string) => (
                        <li key={l}>- {l}</li>
                      ))}
                    </ul>
                  ) : null}
                  {e?.trust_context?.stale_data_note ? (
                    <div className="mt-3 text-xs text-amber-200">
                      Влияние устаревших данных: {String(e.trust_context.stale_data_note)}
                    </div>
                  ) : null}
                </div>

                <div className="mt-4">
                  <div className="text-sm font-semibold">История действий</div>
                  <div className="mt-2 space-y-2 text-xs text-slate-300">
                    {(history.data?.items ?? []).slice(0, 12).map((it) => (
                      <div key={it.id} className="rounded-md border border-slate-800 bg-slate-950/40 p-2">
                        <div className="text-slate-200">{it.event_type}</div>
                        {it.note ? <div className="mt-1">{it.note}</div> : null}
                        <div className="mt-1 text-slate-500">{new Date(it.created_at).toLocaleString("ru-RU")}</div>
                      </div>
                    ))}
                    {!history.isLoading && !(history.data?.items?.length ?? 0) ? (
                      <div className="text-slate-500">История пустая.</div>
                    ) : null}
                  </div>
                </div>
                <div className="mt-4 rounded-lg border border-slate-800/70 bg-slate-950/40 p-3">
                  <div className="text-xs font-medium text-slate-200">Доказательства (evidence)</div>
                  {nodes.length === 0 ? (
                    <div className="mt-2 text-xs text-slate-400">Доказательства не приложены.</div>
                  ) : (
                    <div className="mt-2 space-y-2">
                      {nodes.slice(0, 12).map((n) => (
                        <div key={String(n.node_id)} className="rounded-lg border border-slate-800/60 bg-slate-950/30 p-2">
                          <div className="flex items-center justify-between gap-3">
                            <div className="truncate text-xs text-slate-200">{String(n.label ?? "Доказательство")}</div>
                            <div className="text-[11px] text-slate-500">{String(n.source_type ?? "")}</div>
                          </div>
                          <div className="mt-1 text-[11px] text-slate-400">Источник: {String(n.source_id ?? "")}</div>
                        </div>
                      ))}
                      {edges.length > 0 ? (
                        <div className="text-[11px] text-slate-500">Связей: {edges.length}</div>
                      ) : null}
                    </div>
                  )}
                </div>
                <div className="mt-4 rounded-lg border border-slate-800/70 bg-slate-950/40 p-3">
                  <div className="text-xs font-medium text-slate-200">Инсайты аналитиков (multi-layer)</div>
                  {domainInsights.length === 0 ? (
                    <div className="mt-2 text-xs text-slate-400">
                      Нет инсайтов аналитиков для этой рекомендации (старый прогон или упрощенный режим).
                    </div>
                  ) : (
                    <div className="mt-2 space-y-2">
                      {domainInsights.slice(0, 10).map((ins) => (
                        <div
                          key={String(ins.insight_id ?? ins.analyst_id)}
                          className="rounded-lg border border-slate-800/60 bg-slate-950/30 p-2"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="text-xs font-medium text-slate-200">
                              {String(ins.analyst_label ?? ins.analyst_id ?? "Analyst")}
                            </div>
                            <div className="flex flex-wrap gap-1">
                              <StatusBadge tone="info">P{String(ins.priority_rank ?? "—")}</StatusBadge>
                              <StatusBadge tone="info">
                                {String(ins.confidence ?? "n/a")}
                              </StatusBadge>
                              <StatusBadge
                                tone={
                                  ins.severity === "high" || ins.severity === "critical"
                                    ? "warn"
                                    : "ok"
                                }
                              >
                                {String(ins.severity ?? "low")}
                              </StatusBadge>
                            </div>
                          </div>
                          <div className="mt-1 text-xs text-slate-300">{String(ins.statement ?? "")}</div>
                          {ins.reasoning_summary ? (
                            <div className="mt-1 text-[11px] text-slate-500">{ins.reasoning_summary}</div>
                          ) : null}
                          {(ins.evidence_refs ?? []).length > 0 ? (
                            <div className="mt-1 text-[11px] text-slate-500">
                              Доказательства: {(ins.evidence_refs ?? []).slice(0, 5).join(", ")}
                            </div>
                          ) : null}
                          {(ins.recommended_actions ?? []).length > 0 ? (
                            <ul className="mt-1 list-inside list-disc text-[11px] text-slate-400">
                              {(ins.recommended_actions ?? []).slice(0, 3).map((a, i) => (
                                <li key={i}>{a}</li>
                              ))}
                            </ul>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <div className="mt-3 rounded-lg border border-slate-800/70 bg-slate-950/40 p-3">
                  <div className="text-xs font-medium text-slate-200">Трассировка рассуждений (raw)</div>
                  <pre className="mt-2 max-h-48 overflow-auto text-[11px] text-slate-300">
                    {JSON.stringify(e.reasoning_trace ?? { steps: [] }, null, 2)}
                  </pre>
                </div>
              </>
            ) : (
              <div className="mt-3 text-sm text-slate-300">Объяснимость недоступна.</div>
            )}
          </Card>
        </div>
      ) : (
        <Card className="p-5">Не найдено.</Card>
      )}

      <AiTrustNotice />
    </div>
  );
}

