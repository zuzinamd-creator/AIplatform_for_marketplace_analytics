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
import { CostTrustDisclosure } from "../../ui/cost-trust-disclosure";
import { useProfitTrust } from "../../state/profit-trust";
import { loadWorkspaceProfile } from "../../state/onboarding";
import { toast } from "../../ui/toast";
import { trackUsage } from "../../state/usage";
import {
  confidenceLabelRu,
  eventTypeLabelRu,
  FOLLOW_UP_CHIPS,
  formatDriverCardSummary,
  parseSellerSummarySections,
  pickDriverCards,
  pickPeriodDecision,
  pickSellerAction,
  riskLabelRu,
  type DriverCard,
  type SellerDomainInsight,
} from "../../ui/seller-display";

export function RecommendationDetailPage() {
  const { recommendationId } = useParams();
  const qc = useQueryClient();
  const [overrideReason, setOverrideReason] = useState("");
  const [rating, setRating] = useState<number>(5);
  const [followUp, setFollowUp] = useState("");
  const [conversation, setConversation] = useState<Array<{ q: string; a: string }>>([]);
  const [note, setNote] = useState("");
  const [reminderDate, setReminderDate] = useState<string>("");
  const [showRationale, setShowRationale] = useState(false);
  const [expandedDrivers, setExpandedDrivers] = useState(false);

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

  const r = rec.data as Record<string, unknown> | undefined;
  const e = explain.data as Record<string, unknown> | undefined;
  const plan = (r?.action_plan ?? {}) as Record<string, unknown>;
  const u = (plan.seller_usefulness ?? {}) as Record<string, unknown>;
  const why = String(u.why_this_matters ?? plan.why_this_matters ?? "");
  const action = String(u.concrete_next_action ?? plan.recommended_action ?? "");
  const impact = String(u.expected_business_impact ?? "");
  const upside = String(u.estimated_upside ?? "");
  const downside = String(u.estimated_downside ?? "");
  const urgency = String(u.urgency ?? "");
  const confExplain = String(u.confidence_explanation ?? "");
  const fingerprint = String((r?.lineage as Record<string, unknown> | undefined)?.fingerprint ?? "");
  const businessCoverage = (plan.business_coverage ?? u.business_coverage) as
    | Record<string, unknown>
    | undefined;
  const coverageScore =
    businessCoverage?.business_coverage_score != null
      ? Number(businessCoverage.business_coverage_score)
      : null;

  const explainTrace = e?.reasoning_trace as Record<string, unknown> | undefined;
  const explainGraph = e?.evidence_graph as Record<string, unknown> | undefined;
  const trustContext = (e?.trust_context ?? {}) as Record<string, unknown>;
  const nodes = (explainGraph?.nodes ?? []) as Array<Record<string, unknown>>;
  const edges = (explainGraph?.edges ?? []) as Array<Record<string, unknown>>;
  const domainInsights = (explainTrace?.domain_insights ?? []) as SellerDomainInsight[];
  const summaryText = String(r?.summary ?? "");
  const sections = parseSellerSummarySections(summaryText);
  const displayHeadline = sections.headline || String(r?.title ?? "");
  const displayWhat = sections.whatHappened || summaryText;
  const displayWhy = sections.why || why;
  const limitationsFromSummary = sections.limitations;
  const limitationsFromPlan = String(
    u.analysis_limitations ?? plan.analysis_limitations ?? businessCoverage?.analysis_limitations ?? "",
  );
  const adWarning = String(u.advertising_warning ?? plan.advertising_warning ?? businessCoverage?.advertising_warning ?? "");
  const displayLimitations = [limitationsFromSummary || limitationsFromPlan, adWarning].filter(Boolean).join("\n\n");
  const confLabel = confidenceLabelRu(
    (r?.confidence_score ?? r?.confidence) as string | number | null | undefined,
  );

  const periodDecision = pickPeriodDecision(plan);
  const driverCards = pickDriverCards(plan);

  const workspace = loadWorkspaceProfile();
  const marketplace = workspace.marketplace === "unknown" ? "wildberries" : workspace.marketplace;
  const recPeriodStart = String(u.source_period_start ?? plan.source_period_start ?? "");
  const recPeriodEnd = String(u.source_period_end ?? plan.source_period_end ?? "");

  const recRevenue = useQuery({
    enabled: Boolean(recPeriodStart && recPeriodEnd),
    queryKey: ["costTrust", "recDetail", marketplace, recPeriodStart, recPeriodEnd],
    queryFn: () =>
      api.analytics.revenueSummary({ marketplace, start: recPeriodStart, end: recPeriodEnd }),
  });
  const recCoverage = useQuery({
    enabled: Boolean(recPeriodStart && recPeriodEnd),
    queryKey: ["costTrust", "recDetailCoverage", marketplace, recPeriodStart, recPeriodEnd],
    queryFn: () =>
      api.analytics.costCoverage({ marketplace, start: recPeriodStart, end: recPeriodEnd, limit: 1 }),
  });
  const recCostTrust = useProfitTrust(recRevenue.data?.integrity, recCoverage.data ?? null);
  const todayAction =
    periodDecision?.action ||
    String(u.what_to_do_today ?? u.concrete_next_action ?? plan.recommended_action ?? "");
  const isDataFirst = periodDecision?.mode === "data_first";
  const isSingleOrAlternative =
    Boolean(periodDecision?.action) &&
    (periodDecision?.mode === "single" || periodDecision?.mode === "alternative");
  const displayActionResolved = isSingleOrAlternative
    ? String(periodDecision!.action)
    : isDataFirst
      ? todayAction
      : pickSellerAction(sections.action, todayAction || action);
  const rationaleCard =
    driverCards.find((c) => c.card_id === periodDecision?.source_card_id) ?? driverCards[0];

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-3">
        <div>
          <div className="text-2xl font-semibold">Рекомендация</div>
          <div className="text-sm text-ink-secondary">Доверие к данным, ограничения и история действий продавца.</div>
        </div>
        <Link className="text-sm text-brand hover:underline" to="/app/ai/recommendations">
          Назад
        </Link>
      </div>

      {rec.isLoading ? (
        <Card className="p-5">Загрузка…</Card>
      ) : rec.isError ? (
        <Card className="p-5">Не удалось загрузить рекомендацию.</Card>
      ) : r ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <Card className="p-5 md:col-span-2">
            <div className="text-xs font-semibold uppercase tracking-wide text-brand">
              {isDataFirst ? "Сначала данные" : "Сделайте сегодня"}
            </div>
            <p className="mt-2 text-base font-medium text-ink whitespace-pre-wrap">{displayActionResolved}</p>
            {periodDecision?.alternative_action ? (
              <p className="mt-2 text-sm text-ink-secondary">
                Если не подходит: {periodDecision.alternative_action}
              </p>
            ) : null}
            {periodDecision?.data_request ? (
              <p className="mt-2 text-sm text-amber-200/90">{periodDecision.data_request}</p>
            ) : null}
            {rationaleCard ? (
              <div className="mt-3">
                <button
                  type="button"
                  className="text-sm text-brand hover:underline"
                  onClick={() => setShowRationale((v) => !v)}
                >
                  {showRationale ? "Скрыть обоснование" : "Показать обоснование"}
                </button>
                {showRationale ? (
                  <div className="mt-2 rounded-lg border border-surface-subtle bg-surface-inset p-3 text-sm text-ink-secondary">
                    <div>
                      <span className="font-medium text-ink">SKU:</span> {rationaleCard.sku}
                    </div>
                    {rationaleCard.cause ? <div className="mt-1">{rationaleCard.cause}</div> : null}
                    {rationaleCard.effect_label ? (
                      <div className="mt-1">Потенциальный эффект: {rationaleCard.effect_label}</div>
                    ) : null}
                    {(rationaleCard.checks ?? []).length > 0 ? (
                      <ul className="mt-2 list-inside list-disc text-xs">
                        {(rationaleCard.checks ?? []).map((c, i) => (
                          <li key={i}>{c}</li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ) : null}
              </div>
            ) : null}
          </Card>

          <Card className="p-5">
            <div className="text-sm font-semibold">Суть</div>
            {displayHeadline ? (
              <div className="mt-2 text-base font-medium text-ink">{displayHeadline}</div>
            ) : null}

            <div className="mt-4 space-y-3 text-sm text-ink-secondary">
              {sections.whatHappened || !sections.headline ? (
                <div>
                  <div className="font-medium text-ink-secondary">Что произошло</div>
                  <p className="mt-1">{displayWhat}</p>
                </div>
              ) : null}
              {driverCards.length > 0 ? (
                <div className="rounded-lg border border-surface-subtle bg-surface-inset p-3">
                  <button
                    type="button"
                    className="flex w-full items-center justify-between text-left text-sm font-medium text-ink"
                    onClick={() => setExpandedDrivers((v) => !v)}
                  >
                    <span>Драйверы ({driverCards.length})</span>
                    <span className="text-ink-muted">{expandedDrivers ? "▾" : "▸"}</span>
                  </button>
                  {!expandedDrivers ? (
                    <ul className="mt-2 space-y-1 text-xs text-ink-secondary">
                      {driverCards.map((card: DriverCard) => (
                        <li key={card.card_id ?? card.sku}>{formatDriverCardSummary(card)}</li>
                      ))}
                    </ul>
                  ) : (
                    <div className="mt-3 space-y-3">
                      {driverCards.map((card: DriverCard) => (
                        <div
                          key={card.card_id ?? card.sku}
                          className="rounded border border-surface-subtle bg-surface-inset p-2 text-xs"
                        >
                          <div className="font-medium text-ink">{card.sku}</div>
                          {card.cause ? <div className="mt-1 text-ink-secondary">{card.cause}</div> : null}
                          {card.action ? (
                            <div className="mt-1 text-ink-secondary">
                              <span className="font-medium text-ink">Действие:</span> {card.action}
                            </div>
                          ) : null}
                          {card.effect_label ? (
                            <div className="mt-1 text-ink-muted">Эффект: {card.effect_label}</div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : null}
              {!periodDecision?.action ? (
                <div className="rounded-lg border border-brand/30 bg-brand/5 p-3">
                  <div className="font-medium text-ink">Что делать</div>
                  <p className="mt-1 whitespace-pre-wrap text-ink">{displayActionResolved}</p>
                </div>
              ) : null}
              <div>
                <div className="font-medium text-ink-secondary">Почему это важно</div>
                <p className="mt-1">{displayWhy || "Перед действием проверьте KPI и качество данных."}</p>
              </div>
              {displayLimitations ? (
                <details className="rounded border border-amber-900/40 bg-amber-950/20 p-2 text-xs">
                  <summary className="cursor-pointer font-medium text-amber-100/90">Ограничения анализа</summary>
                  <p className="mt-2 whitespace-pre-wrap text-ink-secondary">{displayLimitations}</p>
                </details>
              ) : null}
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              <StatusBadge tone="info">Уверенность: {confLabel}</StatusBadge>
              <StatusBadge tone="info">Риск: {riskLabelRu(String(r.risk_class ?? ""))}</StatusBadge>
              {r.requires_human_approval ? (
                <StatusBadge tone="warn">Требует подтверждения</StatusBadge>
              ) : (
                <StatusBadge tone="ok">Авто</StatusBadge>
              )}
            </div>

            <div className="mt-4 space-y-3 text-xs text-ink-secondary">
              {urgency ? (
                <div>
                  <span className="font-medium text-ink-secondary">Срочность: </span>
                  {urgency.replace(/_/g, " ")}
                </div>
              ) : null}
              {impact ? (
                <div>
                  <div className="font-medium text-ink-secondary">Ожидаемый эффект</div>
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
              {coverageScore != null ? (
                <div className="rounded border border-surface-subtle bg-surface-inset p-2 text-ink-secondary">
                  <div className="font-medium text-ink-secondary">
                    Покрытие бизнес-данных: {coverageScore.toFixed(0)}%
                  </div>
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

            <div className="mt-6 rounded-lg border border-surface-subtle bg-surface-inset p-3">
              <div className="text-sm font-semibold">Заметка продавца</div>
              <div className="mt-2 space-y-2">
                <Textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Коротко: что и почему нужно сделать…" />
                <div className="flex flex-wrap items-end gap-2">
                  <div className="min-w-[240px]">
                    <Label>Напомнить</Label>
                    <input
                      className="mt-1 h-9 w-full rounded-md border border-surface-subtle bg-surface-inset px-2 text-sm"
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

            <div className="mt-5 rounded-lg border border-surface-subtle bg-surface-inset p-3">
              <div className="text-xs font-medium text-ink-secondary">Задать вопрос по рекомендации</div>
              <p className="mt-1 text-[11px] text-ink0">
                Ответы формируются детерминированно из сохранённых доказательств — без автономных действий на маркетплейсе.
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {FOLLOW_UP_CHIPS.map((chip) => (
                  <button
                    key={chip.id}
                    type="button"
                    className="rounded border border-surface-subtle px-2 py-0.5 text-[11px] text-ink-secondary hover:bg-surface-inset"
                    onClick={() => ask.mutate(chip.id)}
                  >
                    {chip.label}
                  </button>
                ))}
              </div>
              <div className="mt-2 flex gap-2">
                <input
                  className="h-9 flex-1 rounded-lg border border-surface-subtle bg-surface-inset px-3 text-sm"
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
                    <div key={i} className="rounded bg-surface-inset p-2 text-[11px]">
                      <div className="text-ink0">Вопрос: {turn.q}</div>
                      <div className="mt-1 text-ink-secondary">{turn.a}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
            {fingerprint ? (
              <div className="mt-2 text-[11px] text-ink0">
                Идентификатор: <span className="text-ink-muted">{fingerprint.slice(0, 16)}</span>
              </div>
            ) : null}

            <div className="mt-5 space-y-2">
              <div className="text-xs font-medium text-ink-secondary">Оценка полезности</div>
              <div className="flex flex-wrap items-center gap-2">
                <div className="text-xs text-ink-muted">Насколько это полезно?</div>
                <select
                  className="h-9 rounded-lg border border-surface-subtle bg-surface-inset px-3 text-sm text-ink"
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
            {recPeriodStart && recPeriodEnd ? (
              <div className="mt-3">
                <CostTrustDisclosure
                  marketplace={marketplace}
                  start={recPeriodStart}
                  end={recPeriodEnd}
                  className="border-0 bg-transparent p-0 shadow-none"
                />
              </div>
            ) : null}
            {explain.isLoading ? (
              <div className="mt-3 text-sm text-ink-secondary">Загрузка объяснимости…</div>
            ) : e ? (
              <>
                <div className="mt-3">
                  <AiTrustPanel
                    trust={{
                      ...(e.trust_context as Parameters<typeof AiTrustPanel>[0]["trust"]),
                      limitations: [],
                    }}
                    costTrust={recCostTrust}
                  />
                </div>
                <div className="mt-4 rounded-lg border border-surface-subtle bg-surface-inset p-3">
                  <div className="text-sm font-semibold">Почему AI может ошибаться</div>
                  <div className="mt-2 text-sm text-ink-secondary">
                    {String(
                      trustContext.confidence_explanation ??
                        confExplain ??
                        "ИИ даёт рекомендации на основе загруженных отчётов. При неполных данных уверенность снижается.",
                    )}
                  </div>
                  {trustContext.stale_data_note ? (
                    <div className="mt-3 text-xs text-amber-200">
                      Влияние устаревших данных: {String(trustContext.stale_data_note)}
                    </div>
                  ) : null}
                </div>

                <div className="mt-4">
                  <div className="text-sm font-semibold">История действий</div>
                  <div className="mt-2 space-y-2 text-xs text-ink-secondary">
                    {(history.data?.items ?? []).slice(0, 12).map((it) => (
                      <div key={it.id} className="rounded-md border border-surface-subtle bg-surface-inset p-2">
                        <div className="text-ink-secondary">{eventTypeLabelRu(it.event_type)}</div>
                        {it.note ? <div className="mt-1">{it.note}</div> : null}
                        <div className="mt-1 text-ink0">{new Date(it.created_at).toLocaleString("ru-RU")}</div>
                      </div>
                    ))}
                    {!history.isLoading && !(history.data?.items?.length ?? 0) ? (
                      <div className="text-ink0">История пустая.</div>
                    ) : null}
                  </div>
                </div>
                <div className="mt-4 rounded-lg border border-surface-subtle bg-surface-inset p-3">
                  <div className="text-xs font-medium text-ink-secondary">Доказательства</div>
                  {nodes.length === 0 ? (
                    <div className="mt-2 text-xs text-ink-muted">Доказательства не приложены.</div>
                  ) : (
                    <div className="mt-2 space-y-2">
                      {nodes.slice(0, 12).map((n) => (
                        <div key={String(n.node_id)} className="rounded-lg border border-surface-subtle bg-surface-inset p-2">
                          <div className="truncate text-xs text-ink-secondary">{String(n.label ?? "Доказательство")}</div>
                        </div>
                      ))}
                      {edges.length > 0 ? (
                        <div className="text-[11px] text-ink0">Связей между источниками: {edges.length}</div>
                      ) : null}
                    </div>
                  )}
                </div>
                <div className="mt-4 rounded-lg border border-surface-subtle bg-surface-inset p-3">
                  <div className="text-xs font-medium text-ink-secondary">Дополнительные сигналы</div>
                  {domainInsights.length === 0 ? (
                    <div className="mt-2 text-xs text-ink-muted">
                      Нет дополнительных сигналов для этой рекомендации.
                    </div>
                  ) : (
                    <div className="mt-2 space-y-2">
                      {domainInsights.slice(0, 10).map((ins) => (
                        <div
                          key={String(ins.insight_id ?? ins.domain)}
                          className="rounded-lg border border-surface-subtle bg-surface-inset p-2"
                        >
                          <div className="text-xs font-medium text-ink-secondary">
                            {String(ins.domain ?? "Сигнал по данным")}
                          </div>
                          <div className="mt-1 text-xs text-ink-secondary">{String(ins.statement ?? "")}</div>
                          {ins.why_it_matters ? (
                            <div className="mt-1 text-[11px] text-ink0">{ins.why_it_matters}</div>
                          ) : null}
                          {(ins.recommended_actions ?? []).length > 0 ? (
                            <ul className="mt-1 list-inside list-disc text-[11px] text-ink-muted">
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
              </>
            ) : (
              <div className="mt-3 text-sm text-ink-secondary">Объяснимость недоступна.</div>
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

