import { describe, expect, it } from "vitest";

import {
  RETURNS_PRESSURE_THRESHOLD_PCT,
  buildBusinessSignals,
  buildCostStructureSignal,
  buildReturnsSignal,
  buildSkuAttentionSignal,
  dominantExpense,
  returnsPressurePct,
} from "./business-signals";

describe("dominantExpense", () => {
  it("picks the largest fee category and share of total expenses", () => {
    const dom = dominantExpense({
      commission: "430",
      logistics: "200",
      advertisement: "100",
      storage_fee: "50",
      penalties: "0",
      deductions: "100",
      acquiring: "50",
      other: "70",
    });
    expect(dom?.key).toBe("commission");
    expect(dom?.label).toBe("Комиссия WB");
    expect(dom?.sharePct).toBeCloseTo(43, 5);
  });

  it("returns null when all expenses are zero", () => {
    expect(dominantExpense({ commission: "0", logistics: "0" })).toBeNull();
  });
});

describe("buildCostStructureSignal", () => {
  it("formats dominant expense share", () => {
    const signal = buildCostStructureSignal({
      commission: "430",
      logistics: "200",
      advertisement: "100",
      storage_fee: "50",
      deductions: "100",
      acquiring: "50",
      other: "70",
    });
    expect(signal?.id).toBe("cost");
    expect(signal?.text).toBe("Комиссия WB составляет 43% всех расходов за период.");
  });
});

describe("returnsPressurePct / buildReturnsSignal", () => {
  it("uses return_rate_pct when present", () => {
    expect(
      returnsPressurePct({
        sales_revenue: "1000",
        returns_amount: "50",
        return_rate_pct: "11.2",
      }),
    ).toBeCloseTo(11.2);
  });

  it("falls back to returns/revenue", () => {
    expect(
      returnsPressurePct({ sales_revenue: "1000", returns_amount: "120" }),
    ).toBeCloseTo(12);
  });

  it("emits signal only above threshold", () => {
    expect(RETURNS_PRESSURE_THRESHOLD_PCT).toBe(10);
    expect(
      buildReturnsSignal({ sales_revenue: "1000", returns_amount: "90" }),
    ).toBeNull();
    const signal = buildReturnsSignal({ sales_revenue: "1000", returns_amount: "110" });
    expect(signal?.text).toBe("Возвраты достигли 11% от выручки и требуют внимания.");
  });
});

describe("buildSkuAttentionSignal", () => {
  const items = [
    { sku: "SKU-A", revenue: "100000", net_profit: "20000", margin_pct: "20" },
    { sku: "SKU-B", revenue: "80000", net_profit: "1000", margin_pct: "1.2" },
  ];

  it("flags high-revenue low-margin SKU", () => {
    const signal = buildSkuAttentionSignal(items, { trustInsufficient: false });
    expect(signal?.text).toBe("SKU SKU-B имеет высокую выручку при низкой марже.");
  });

  it("hides SKU signal when profit trust is insufficient", () => {
    expect(buildSkuAttentionSignal(items, { trustInsufficient: true })).toBeNull();
  });

  it("returns null when no SKU needs attention", () => {
    expect(
      buildSkuAttentionSignal(
        [{ sku: "SKU-OK", revenue: "100", net_profit: "40", margin_pct: "40" }],
        { trustInsufficient: false },
      ),
    ).toBeNull();
  });
});

describe("buildBusinessSignals", () => {
  it("orders cost → returns → sku and caps at 3", () => {
    const signals = buildBusinessSignals({
      financeKpis: {
        commission: "500",
        logistics: "100",
        sales_revenue: "1000",
        returns_amount: "150",
        return_rate_pct: "15",
      },
      topSkus: [
        { sku: "SKU-A", revenue: "100", net_profit: "40", margin_pct: "40" },
        { sku: "SKU-WEAK", revenue: "90", net_profit: "-5", margin_pct: "-5" },
      ],
      trustInsufficient: false,
    });
    expect(signals.map((s) => s.id)).toEqual(["cost", "returns", "sku"]);
  });

  it("omits sku when trust insufficient but keeps cost/returns", () => {
    const signals = buildBusinessSignals({
      financeKpis: {
        commission: "500",
        logistics: "100",
        sales_revenue: "1000",
        returns_amount: "150",
      },
      topSkus: [{ sku: "SKU-WEAK", revenue: "100", net_profit: "-5", margin_pct: "-5" }],
      trustInsufficient: true,
    });
    expect(signals.map((s) => s.id)).toEqual(["cost", "returns"]);
  });
});
