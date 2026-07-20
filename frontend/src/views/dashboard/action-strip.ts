/** Deterministic Action Strip card builder (Phase 9.18-F2-B). */

import {
  COSTS_WORKFLOW_ROUTE,
  type ProfitTrustContext,
} from "../../state/profit-trust";
import { formatMetric, formatPct } from "../../utils/format";
import { buildBusinessSignals, type BusinessSignal } from "./business-signals";

export const ACTION_STRIP_MAX_CARDS = 3;
export const COST_SECTION_ANCHOR = "dashboard-cost-structure";

export type ActionCardId =
  | "trust-blocker"
  | "dangerous-0"
  | "dangerous-1"
  | "signal-cost"
  | "signal-returns"
  | "signal-sku"
  | "ai-count"
  | "costs-nudge"
  | "empty";

export type ActionCard = {
  id: ActionCardId;
  title: string;
  body: string;
  ctaLabel: string;
  ctaHref: string;
};

export type BuildActionCardsInput = {
  trustCtx: ProfitTrustContext;
  dangerous: string[];
  signals: BusinessSignal[];
  aiRecommendationCount: number;
  /** When true, skip trust-blocker (Trust badge already on Primary Answer). */
  omitTrustBlocker?: boolean;
};

export type BuildActionCardsFromSummaryInput = {
  trustCtx: ProfitTrustContext;
  dangerous?: string[] | null;
  financeKpis?: Parameters<typeof buildBusinessSignals>[0]["financeKpis"];
  topSkus?: Parameters<typeof buildBusinessSignals>[0]["topSkus"];
  aiRecommendationCount: number;
  omitTrustBlocker?: boolean;
};

function trustBlockerTitle(trust: ProfitTrustContext["trust"]): string {
  switch (trust) {
    case "partial":
      return "Себестоимость неполная";
    case "insufficient":
      return "Нет себестоимости";
    case "full":
      return "Проверено";
  }
}

function trustBlockerBody(ctx: ProfitTrustContext): string {
  const parts: string[] = [];
  if (ctx.coveragePct !== null) {
    parts.push(`Покрытие: ${formatPct(ctx.coveragePct)}`);
  }
  if (ctx.coveredSkus !== null && ctx.totalSkus !== null) {
    parts.push(`${formatMetric(ctx.coveredSkus)} из ${formatMetric(ctx.totalSkus)} SKU`);
  }
  if (parts.length) {
    return parts.join(" · ");
  }
  if (ctx.trust === "insufficient") {
    return "Загрузите себестоимость, чтобы увидеть прибыль и маржу.";
  }
  return "Прибыль рассчитана не для всех SKU.";
}

function buildTrustBlockerCard(ctx: ProfitTrustContext): ActionCard {
  return {
    id: "trust-blocker",
    title: trustBlockerTitle(ctx.trust),
    body: trustBlockerBody(ctx),
    ctaLabel: "Уточнить себестоимость",
    ctaHref: COSTS_WORKFLOW_ROUTE,
  };
}

function buildDangerousCard(index: 0 | 1, message: string): ActionCard {
  return {
    id: index === 0 ? "dangerous-0" : "dangerous-1",
    title: "Требует внимания",
    body: message,
    ctaLabel: "Открыть брифинг",
    ctaHref: "/app/today",
  };
}

function buildSignalCard(id: BusinessSignal["id"], signal: BusinessSignal): ActionCard {
  switch (id) {
    case "cost":
      return {
        id: "signal-cost",
        title: "Структура расходов",
        body: signal.text,
        ctaLabel: "Смотреть расходы",
        ctaHref: `/app/analytics#${COST_SECTION_ANCHOR}`,
      };
    case "returns":
      return {
        id: "signal-returns",
        title: "Возвраты",
        body: signal.text,
        ctaLabel: "Экономика SKU",
        ctaHref: "/app/analytics/economics",
      };
    case "sku":
      return {
        id: "signal-sku",
        title: "SKU под риском",
        body: signal.text,
        ctaLabel: "Открыть SKU",
        ctaHref: "/app/analytics/economics",
      };
  }
}

function buildAiCountCard(count: number): ActionCard {
  return {
    id: "ai-count",
    title: "ИИ-рекомендации",
    body: `Доступно рекомендаций: ${formatMetric(count)}`,
    ctaLabel: "Открыть",
    ctaHref: "/app/ai/recommendations",
  };
}

export function buildEmptyStateCard(): ActionCard {
  return {
    id: "empty",
    title: "Сейчас без срочных действий",
    body: "Показатели в пределах нормы за выбранный период.",
    ctaLabel: "Открыть брифинг",
    ctaHref: "/app/today",
  };
}

/** Fallback when priority chain is empty and trust ≠ full (variant B — no priority reorder). */
export function buildCostsNudgeCard(): ActionCard {
  return {
    id: "costs-nudge",
    title: "Добавьте себестоимость",
    body: "Чтобы видеть прибыль и маржу",
    ctaLabel: "Загрузить себестоимость",
    ctaHref: COSTS_WORKFLOW_ROUTE,
  };
}

/** Priority: trust-blocker → dangerous[0..1] → signal-cost → signal-returns → signal-sku → ai-count. Max 3.
 *  Empty fallback: costs-nudge when trust ≠ full; generic empty when trust === full.
 */
export function buildActionCards(input: BuildActionCardsInput): ActionCard[] {
  const cards: ActionCard[] = [];

  if (
    !input.omitTrustBlocker &&
    input.trustCtx.trust !== "full" &&
    cards.length < ACTION_STRIP_MAX_CARDS
  ) {
    cards.push(buildTrustBlockerCard(input.trustCtx));
  }

  for (let i = 0; i < 2 && cards.length < ACTION_STRIP_MAX_CARDS; i += 1) {
    const message = input.dangerous[i]?.trim();
    if (message) {
      cards.push(buildDangerousCard(i as 0 | 1, message));
    }
  }

  const signalOrder: BusinessSignal["id"][] = ["cost", "returns", "sku"];
  const signalById = new Map(input.signals.map((signal) => [signal.id, signal]));
  for (const signalId of signalOrder) {
    if (cards.length >= ACTION_STRIP_MAX_CARDS) break;
    const signal = signalById.get(signalId);
    if (signal) {
      cards.push(buildSignalCard(signalId, signal));
    }
  }

  if (input.aiRecommendationCount > 0 && cards.length < ACTION_STRIP_MAX_CARDS) {
    cards.push(buildAiCountCard(input.aiRecommendationCount));
  }

  if (cards.length === 0) {
    if (input.trustCtx.trust !== "full") {
      return [buildCostsNudgeCard()];
    }
    return [buildEmptyStateCard()];
  }

  return cards;
}

/** Convenience wrapper using existing summary fields and buildBusinessSignals(). */
export function buildActionCardsFromSummary(input: BuildActionCardsFromSummaryInput): ActionCard[] {
  const signals = buildBusinessSignals({
    financeKpis: input.financeKpis ?? null,
    topSkus: input.topSkus ?? null,
    trustInsufficient: input.trustCtx.trust === "insufficient",
  });

  return buildActionCards({
    trustCtx: input.trustCtx,
    dangerous: input.dangerous ?? [],
    signals,
    aiRecommendationCount: input.aiRecommendationCount,
    omitTrustBlocker: input.omitTrustBlocker,
  });
}
