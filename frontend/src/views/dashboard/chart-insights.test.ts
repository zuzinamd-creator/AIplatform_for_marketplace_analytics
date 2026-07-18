import { describe, expect, it } from "vitest";

import {
  costDynamicsInsight,
  costStructureInsight,
  formatInsightDay,
  insightDateKey,
  revenueProfitInsight,
  topSkuInsight,
} from "./chart-insights";
import { buildPeriodCostComposition } from "./cost-structure-chart";

describe("formatInsightDay", () => {
  it("formats ISO and chart dates as DD.MM", () => {
    expect(formatInsightDay("2026-06-18")).toBe("18.06");
    expect(formatInsightDay("06-21")).toBe("21.06");
  });
});

describe("insightDateKey", () => {
  it("normalizes ISO dates", () => {
    expect(insightDateKey("2026-06-24")).toBe("2026-06-24");
  });
});

describe("revenueProfitInsight", () => {
  it("reports relative drop vs average with cost driver and attention", () => {
    const text = revenueProfitInsight(
      [
        { date: "2026-06-10", revenue: "100", seller_profit: "50" },
        { date: "2026-06-17", revenue: "100", seller_profit: "50" },
        { date: "2026-06-24", revenue: "100", seller_profit: "20" },
      ],
      true,
      [
        {
          date: "2026-06-10",
          logistics: "10",
          commission: "5",
          advertisement: "0",
          storage_fee: "0",
          penalties: "0",
          deductions: "0",
          acquiring: "0",
          other: "0",
        },
        {
          date: "2026-06-17",
          logistics: "10",
          commission: "5",
          advertisement: "0",
          storage_fee: "0",
          penalties: "0",
          deductions: "0",
          acquiring: "0",
          other: "0",
        },
        {
          date: "2026-06-24",
          logistics: "40",
          commission: "5",
          advertisement: "0",
          storage_fee: "0",
          penalties: "0",
          deductions: "0",
          acquiring: "0",
          other: "0",
        },
      ],
    );
    // avg profit = 40; day 24 = 20 → 50% drop
    expect(text).toMatch(/24\.06 прибыль снизилась на 50% относительно среднего уровня периода/);
    expect(text).toMatch(/из-за роста логистических расходов/);
    expect(text).toMatch(/Стоит проверить этот день/);
  });

  it("falls back to revenue metric when profit hidden", () => {
    const text = revenueProfitInsight(
      [
        { date: "2026-06-10", revenue: "100", net_profit: null },
        { date: "2026-06-12", revenue: "100", net_profit: null },
        { date: "2026-06-14", revenue: "40", net_profit: null },
      ],
      false,
    );
    expect(text).toMatch(/14\.06 выручка снизилась на/);
    expect(text).toMatch(/относительно среднего уровня периода/);
  });

  it("reports stable period when no material deviation", () => {
    const text = revenueProfitInsight(
      [
        { date: "2026-06-10", revenue: "100", seller_profit: "40" },
        { date: "2026-06-11", revenue: "100", seller_profit: "42" },
        { date: "2026-06-12", revenue: "100", seller_profit: "41" },
      ],
      true,
    );
    expect(text).toBe("За период прибыль без резких отклонений относительно среднего уровня.");
  });

  it("hides when empty", () => {
    expect(revenueProfitInsight([], true)).toBeNull();
  });
});

describe("costStructureInsight", () => {
  it("names leader with share and concentration attention", () => {
    const comp = buildPeriodCostComposition({ commission: "430", logistics: "200" });
    const text = costStructureInsight(comp);
    expect(text).toMatch(/Комиссия WB занимает 68% всех расходов/);
    expect(text).toMatch(/крупнейшей статьёй затрат/);
    expect(text).toMatch(/Статья доминирует|Высокая концентрация/);
  });

  it("uses distributed wording when there is no clear leader", () => {
    const comp = buildPeriodCostComposition({
      commission: "22",
      logistics: "21",
      advertisement: "20",
      storage_fee: "19",
      deductions: "18",
    });
    expect(costStructureInsight(comp)).toMatch(/Расходы распределены: лидер/);
  });
});

describe("costDynamicsInsight", () => {
  it("reports dominant single-category day", () => {
    expect(
      costDynamicsInsight([
        {
          date: "06-18",
          total_costs: 20,
          commission: 10,
          logistics: 10,
          advertisement: 0,
          storage: 0,
          penalties: 0,
          deductions: 0,
          acquiring: 0,
          other: 0,
        },
        {
          date: "06-21",
          total_costs: 100,
          commission: 10,
          logistics: 90,
          advertisement: 0,
          storage: 0,
          penalties: 0,
          deductions: 0,
          acquiring: 0,
          other: 0,
        },
      ]),
    ).toBe("21.06 почти все расходы дня составила логистика (90%).");
  });

  it("reports spike vs average with dominant category", () => {
    expect(
      costDynamicsInsight([
        {
          date: "06-18",
          total_costs: 30,
          commission: 15,
          logistics: 15,
          advertisement: 0,
          storage: 0,
          penalties: 0,
          deductions: 0,
          acquiring: 0,
          other: 0,
        },
        {
          date: "06-19",
          total_costs: 30,
          commission: 15,
          logistics: 15,
          advertisement: 0,
          storage: 0,
          penalties: 0,
          deductions: 0,
          acquiring: 0,
          other: 0,
        },
        {
          date: "06-21",
          total_costs: 120,
          commission: 50,
          logistics: 70,
          advertisement: 0,
          storage: 0,
          penalties: 0,
          deductions: 0,
          acquiring: 0,
          other: 0,
        },
      ]),
    ).toMatch(/21\.06 расходы были в 2 раза выше среднего уровня периода/);
  });
});

describe("topSkuInsight", () => {
  it("flags business dependency for high contribution", () => {
    expect(
      topSkuInsight([{ sku: "Товар X", contribution_pct: "61" }, { sku: "Y", contribution_pct: "10" }]),
    ).toBe("Товар X формирует 61% выручки периода. Бизнес существенно зависит от одного товара.");
  });

  it("notes normal concentration for modest share", () => {
    expect(topSkuInsight([{ sku: "Товар X", contribution_pct: "18" }])).toBe(
      "Товар X формирует 18% выручки периода. Концентрация выручки в норме.",
    );
  });

  it("hides without contribution", () => {
    expect(topSkuInsight([{ sku: "X", contribution_pct: null }])).toBeNull();
  });
});
