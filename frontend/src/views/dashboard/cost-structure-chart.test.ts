import { describe, expect, it } from "vitest";

import {
  COST_STRUCTURE_CORE_SERIES,
  costStructureSeriesFor,
  hasNonZeroOther,
  mapFinanceTrendToCostStructure,
} from "./cost-structure-chart";

describe("mapFinanceTrendToCostStructure", () => {
  it("maps explicit segments and does not include payout or other_costs", () => {
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
    expect(rows).toHaveLength(1);
    expect(rows[0]).toEqual({
      date: "07-15",
      commission: 90,
      logistics: 12,
      advertisement: 15,
      returns: 50,
      storage: 3,
      penalties: 4,
      deductions: 5,
      acquiring: 6,
      other: 7,
    });
    expect(rows[0]).not.toHaveProperty("payout");
    expect(rows[0]).not.toHaveProperty("other_costs");
  });

  it("defaults missing B1 fields to 0 (backward compatibility)", () => {
    const rows = mapFinanceTrendToCostStructure([
      {
        date: "2026-05-01",
        logistics: "10",
        advertisement: "20",
        returns_amount: "30",
        payout: "100",
      },
    ]);
    expect(rows[0].commission).toBe(0);
    expect(rows[0].storage).toBe(0);
    expect(rows[0].penalties).toBe(0);
    expect(rows[0].deductions).toBe(0);
    expect(rows[0].acquiring).toBe(0);
    expect(rows[0].other).toBe(0);
    expect(rows[0].logistics).toBe(10);
  });
});

describe("costStructureSeriesFor", () => {
  it("exposes Russian labels without payout; core stack is 8 segments", () => {
    const names = COST_STRUCTURE_CORE_SERIES.map((s) => s.name);
    expect(names).toEqual([
      "Комиссия",
      "Логистика",
      "Продвижение",
      "Возвраты",
      "Хранение",
      "Штрафы",
      "Удержания",
      "Эквайринг",
    ]);
    expect(COST_STRUCTURE_CORE_SERIES.some((s) => s.dataKey === "payout")).toBe(false);
  });

  it("omits Прочее when other is zero everywhere", () => {
    const rows = mapFinanceTrendToCostStructure([
      { date: "2026-07-01", commission: "1", storage_fee: "2", other: "0" },
    ]);
    expect(hasNonZeroOther(rows)).toBe(false);
    expect(costStructureSeriesFor(rows).map((s) => s.name)).not.toContain("Прочее");
  });

  it("includes Прочее when other is non-zero", () => {
    const rows = mapFinanceTrendToCostStructure([
      { date: "2026-07-01", other: "1.5" },
    ]);
    expect(hasNonZeroOther(rows)).toBe(true);
    const series = costStructureSeriesFor(rows);
    expect(series.map((s) => s.name)).toContain("Прочее");
    expect(series.at(-1)?.dataKey).toBe("other");
  });
});
