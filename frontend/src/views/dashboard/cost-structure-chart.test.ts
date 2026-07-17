import { describe, expect, it } from "vitest";

import {
  buildDailyCostChart,
  buildPeriodCostComposition,
  COST_CATEGORIES,
  mapFinanceTrendToCostStructure,
} from "./cost-structure-chart";

describe("buildPeriodCostComposition", () => {
  it("ranks categories by amount and includes Удержания hint", () => {
    const comp = buildPeriodCostComposition({
      commission: "430",
      logistics: "200",
      advertisement: "100",
      returns_amount: "50",
      storage_fee: "20",
      penalties: "10",
      deductions: "80",
      acquiring: "30",
    });
    expect(comp.total).toBe(920);
    expect(comp.slices[0].key).toBe("commission");
    expect(comp.slices[0].sharePct).toBeCloseTo((430 / 920) * 100, 5);
    const deductions = comp.slices.find((s) => s.key === "deductions");
    expect(deductions?.name).toBe("Удержания");
    expect(deductions?.hint.toLowerCase()).toContain("списан");
  });

  it("omits zero categories", () => {
    const comp = buildPeriodCostComposition({ commission: "100", logistics: "0" });
    expect(comp.slices.map((s) => s.key)).toEqual(["commission"]);
  });
});

describe("buildDailyCostChart", () => {
  it("keeps top categories and bags the rest", () => {
    const { rows, series } = buildDailyCostChart(
      [
        {
          date: "2026-07-01",
          commission: "100",
          logistics: "40",
          advertisement: "30",
          returns_amount: "20",
          storage_fee: "5",
          penalties: "4",
          deductions: "3",
          acquiring: "2",
          other: "1",
        },
      ],
      3,
    );
    expect(series.map((s) => s.dataKey).slice(0, 3)).toEqual([
      "commission",
      "logistics",
      "advertisement",
    ]);
    expect(series.some((s) => s.dataKey === "rest")).toBe(true);
    expect(rows[0].commission).toBe(100);
    expect(rows[0].rest).toBe(20 + 5 + 4 + 3 + 2 + 1);
  });
});

describe("mapFinanceTrendToCostStructure", () => {
  it("maps segments and does not include payout", () => {
    const rows = mapFinanceTrendToCostStructure([
      {
        date: "2026-07-15",
        commission: "90",
        logistics: "12",
        advertisement: "15",
        returns_amount: "50",
        payout: "800",
        storage_fee: "3",
        penalties: "4",
        deductions: "5",
        acquiring: "6",
        other: "7",
      },
    ]);
    expect(rows[0]).not.toHaveProperty("payout");
    expect(rows[0].commission).toBe(90);
  });
});

describe("COST_CATEGORIES", () => {
  it("explains Удержания in seller language", () => {
    const d = COST_CATEGORIES.find((c) => c.key === "deductions");
    expect(d?.name).toBe("Удержания");
    expect(d?.hint.length).toBeGreaterThan(10);
  });
});
