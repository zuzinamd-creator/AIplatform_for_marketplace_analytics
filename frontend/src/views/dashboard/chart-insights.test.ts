import { describe, expect, it } from "vitest";

import {
  costDynamicsInsight,
  costStructureInsight,
  formatInsightDay,
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

describe("revenueProfitInsight", () => {
  it("reports max profit day when profit is shown", () => {
    const text = revenueProfitInsight(
      [
        { date: "2026-06-10", revenue: "100", seller_profit: "10" },
        { date: "2026-06-18", revenue: "80", seller_profit: "40" },
      ],
      true,
    );
    expect(text).toBe("Максимальная прибыль была 18.06.");
  });

  it("falls back to peak revenue when profit hidden", () => {
    const text = revenueProfitInsight(
      [
        { date: "2026-06-10", revenue: "100", net_profit: null },
        { date: "2026-06-12", revenue: "250", net_profit: null },
      ],
      false,
    );
    expect(text).toBe("Пик выручки: 12.06.");
  });

  it("hides when empty", () => {
    expect(revenueProfitInsight([], true)).toBeNull();
  });
});

describe("costStructureInsight", () => {
  it("names the leader without a percentage (de-dup vs Business Signals)", () => {
    const comp = buildPeriodCostComposition({ commission: "430", logistics: "200" });
    expect(costStructureInsight(comp)).toBe("Основная часть расходов приходится на комиссию WB.");
    expect(costStructureInsight(comp)).not.toMatch(/%/);
    expect(costStructureInsight(comp)).not.toMatch(/составляет/);
  });

  it("uses concentrated wording for a moderate leader", () => {
    const comp = buildPeriodCostComposition({
      commission: "30",
      logistics: "25",
      advertisement: "20",
      storage_fee: "15",
      deductions: "10",
    });
    // top = 30% → between 25 and 40
    expect(costStructureInsight(comp)).toBe(
      "Структура расходов концентрирована вокруг одной статьи затрат.",
    );
    expect(costStructureInsight(comp)).not.toMatch(/%/);
  });

  it("uses distributed wording when there is no clear leader", () => {
    const comp = buildPeriodCostComposition({
      commission: "22",
      logistics: "21",
      advertisement: "20",
      storage_fee: "19",
      deductions: "18",
    });
    expect(costStructureInsight(comp)).toBe(
      "Расходы распределены между несколькими категориями без явного лидера.",
    );
  });
});

describe("costDynamicsInsight", () => {
  it("reports peak cost day", () => {
    expect(
      costDynamicsInsight([
        {
          date: "06-18",
          total_costs: 10,
          commission: 10,
          logistics: 0,
          advertisement: 0,
          storage: 0,
          penalties: 0,
          deductions: 0,
          acquiring: 0,
          other: 0,
        },
        {
          date: "06-21",
          total_costs: 90,
          commission: 40,
          logistics: 50,
          advertisement: 0,
          storage: 0,
          penalties: 0,
          deductions: 0,
          acquiring: 0,
          other: 0,
        },
      ]),
    ).toBe("Пик расходов пришёлся на 21.06.");
  });
});

describe("topSkuInsight", () => {
  it("reports contribution of the leader", () => {
    expect(
      topSkuInsight([{ sku: "Товар X", contribution_pct: "38.2" }, { sku: "Y", contribution_pct: "10" }]),
    ).toBe("Товар X формирует 38% выручки периода.");
  });

  it("hides without contribution", () => {
    expect(topSkuInsight([{ sku: "X", contribution_pct: null }])).toBeNull();
  });
});
