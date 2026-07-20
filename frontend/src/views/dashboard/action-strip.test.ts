import { describe, expect, it } from "vitest";

import type { ProfitTrustContext } from "../../state/profit-trust";
import {
  ACTION_STRIP_MAX_CARDS,
  buildActionCards,
  buildEmptyStateCard,
  type BuildActionCardsInput,
} from "./action-strip";

function ctx(overrides: Partial<ProfitTrustContext> = {}): ProfitTrustContext {
  return {
    trust: "partial",
    coveragePct: 72,
    coveredSkus: 18,
    totalSkus: 25,
    missingSkus: ["SKU-1"],
    canShowProfit: true,
    canShowMargin: false,
    canShowProfitAction: false,
    ...overrides,
  };
}

function input(overrides: Partial<BuildActionCardsInput> = {}): BuildActionCardsInput {
  return {
    trustCtx: ctx(),
    dangerous: [],
    signals: [],
    aiRecommendationCount: 0,
    ...overrides,
  };
}

describe("buildActionCards", () => {
  it("prioritizes trust-blocker first", () => {
    const cards = buildActionCards(
      input({
        signals: [{ id: "cost", text: "Комиссия WB составляет 46% всех расходов за период." }],
        aiRecommendationCount: 5,
      }),
    );

    expect(cards[0]?.id).toBe("trust-blocker");
    expect(cards[0]?.ctaHref).toBe("/app/costs");
    expect(cards[0]?.ctaLabel).toBe("Уточнить себестоимость");
  });

  it("omits trust-blocker when Trust badge is on Primary Answer", () => {
    const cards = buildActionCards(
      input({
        omitTrustBlocker: true,
        signals: [{ id: "cost", text: "Комиссия WB составляет 46% всех расходов за период." }],
      }),
    );

    expect(cards.some((card) => card.id === "trust-blocker")).toBe(false);
    expect(cards[0]?.id).toBe("signal-cost");
  });

  it("does not emit trust-blocker when trust is full", () => {
    const cards = buildActionCards(
      input({
        trustCtx: ctx({ trust: "full", canShowMargin: true, canShowProfitAction: true }),
        signals: [{ id: "cost", text: "Комиссия WB составляет 46% всех расходов за период." }],
      }),
    );

    expect(cards.some((card) => card.id === "trust-blocker")).toBe(false);
    expect(cards[0]?.id).toBe("signal-cost");
  });

  it("prioritizes dangerous flags after trust-blocker", () => {
    const cards = buildActionCards(
      input({
        dangerous: ["Просрочен отчёт", "Низкая маржа по SKU-A"],
        signals: [{ id: "cost", text: "Комиссия WB составляет 46% всех расходов за период." }],
      }),
    );

    expect(cards.map((card) => card.id)).toEqual(["trust-blocker", "dangerous-0", "dangerous-1"]);
    expect(cards[1]?.body).toBe("Просрочен отчёт");
    expect(cards[1]?.ctaHref).toBe("/app/today");
    expect(cards[2]?.body).toBe("Низкая маржа по SKU-A");
  });

  it("prioritizes signals cost → returns → sku after dangerous items", () => {
    const cards = buildActionCards(
      input({
        trustCtx: ctx({ trust: "full", canShowMargin: true, canShowProfitAction: true }),
        signals: [
          { id: "sku", text: "SKU SKU-WEAK имеет высокую выручку при низкой марже." },
          { id: "returns", text: "Возвраты достигли 12% от выручки и требуют внимания." },
          { id: "cost", text: "Комиссия WB составляет 46% всех расходов за период." },
        ],
      }),
    );

    expect(cards.map((card) => card.id)).toEqual(["signal-cost", "signal-returns", "signal-sku"]);
    expect(cards[0]?.ctaHref).toBe("/app/analytics#dashboard-cost-structure");
    expect(cards[1]?.ctaHref).toBe("/app/analytics/economics");
    expect(cards[2]?.ctaHref).toBe("/app/analytics/economics");
  });

  it("uses ai-count only when slots remain", () => {
    const cards = buildActionCards(
      input({
        trustCtx: ctx({ trust: "full", canShowMargin: true, canShowProfitAction: true }),
        dangerous: ["Флаг 1", "Флаг 2"],
        signals: [{ id: "cost", text: "Комиссия WB составляет 46% всех расходов за период." }],
        aiRecommendationCount: 4,
      }),
    );

    expect(cards.map((card) => card.id)).toEqual(["dangerous-0", "dangerous-1", "signal-cost"]);
    expect(cards.some((card) => card.id === "ai-count")).toBe(false);
  });

  it("falls back to ai-count when higher-priority sources are absent", () => {
    const cards = buildActionCards(
      input({
        trustCtx: ctx({ trust: "full", canShowMargin: true, canShowProfitAction: true }),
        aiRecommendationCount: 3,
      }),
    );

    expect(cards).toEqual([
      {
        id: "ai-count",
        title: "ИИ-рекомендации",
        body: "Доступно рекомендаций: 3",
        ctaLabel: "Открыть",
        ctaHref: "/app/ai/recommendations",
      },
    ]);
  });

  it(`caps output at ${ACTION_STRIP_MAX_CARDS} cards`, () => {
    const cards = buildActionCards(
      input({
        dangerous: ["Флаг 1", "Флаг 2"],
        signals: [
          { id: "cost", text: "Комиссия WB составляет 46% всех расходов за период." },
          { id: "returns", text: "Возвраты достигли 12% от выручки и требуют внимания." },
          { id: "sku", text: "SKU SKU-WEAK имеет высокую выручку при низкой марже." },
        ],
        aiRecommendationCount: 9,
      }),
    );

    expect(cards).toHaveLength(ACTION_STRIP_MAX_CARDS);
    expect(cards.map((card) => card.id)).toEqual(["trust-blocker", "dangerous-0", "dangerous-1"]);
  });

  it("returns empty state card when no sources match", () => {
    const cards = buildActionCards(
      input({
        trustCtx: ctx({ trust: "full", canShowMargin: true, canShowProfitAction: true }),
      }),
    );

    expect(cards).toEqual([buildEmptyStateCard()]);
    expect(cards[0]?.ctaHref).toBe("/app/today");
    expect(cards[0]?.ctaLabel).toBe("Открыть брифинг");
  });

  it("variant B: costs-nudge instead of empty when trust ≠ full and chain is empty", () => {
    const cards = buildActionCards(
      input({
        omitTrustBlocker: true,
        trustCtx: ctx({
          trust: "insufficient",
          coveragePct: 0,
          coveredSkus: 0,
          totalSkus: 2,
          canShowProfit: false,
        }),
      }),
    );

    expect(cards).toEqual([
      {
        id: "costs-nudge",
        title: "Добавьте себестоимость",
        body: "Чтобы видеть прибыль и маржу",
        ctaLabel: "Загрузить себестоимость",
        ctaHref: "/app/costs",
      },
    ]);
  });

  it("variant B: partial trust also gets costs-nudge when chain is empty", () => {
    const cards = buildActionCards(
      input({
        omitTrustBlocker: true,
        trustCtx: ctx({ trust: "partial" }),
      }),
    );

    expect(cards).toHaveLength(1);
    expect(cards[0]?.id).toBe("costs-nudge");
  });

  it("variant B: does not displace dangerous or signal cards", () => {
    const cards = buildActionCards(
      input({
        omitTrustBlocker: true,
        trustCtx: ctx({ trust: "insufficient", canShowProfit: false }),
        dangerous: ["Просрочен отчёт"],
      }),
    );

    expect(cards.map((c) => c.id)).toEqual(["dangerous-0"]);
    expect(cards.some((c) => c.id === "costs-nudge")).toBe(false);
  });

  it("maps insufficient trust title and coverage body", () => {
    const cards = buildActionCards(
      input({
        trustCtx: ctx({
          trust: "insufficient",
          coveragePct: 0,
          coveredSkus: 0,
          totalSkus: 5,
          canShowProfit: false,
        }),
      }),
    );

    expect(cards[0]?.title).toBe("Нет себестоимости");
    expect(cards[0]?.body).toMatch(/Покрытие:/);
    expect(cards[0]?.body).toMatch(/0 из 5 SKU/);
  });
});
