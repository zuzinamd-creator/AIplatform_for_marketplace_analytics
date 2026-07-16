import { describe, expect, it } from "vitest";

import { skuNeedsAttention, topSkuApiSortParam } from "./top-sku-attention";

describe("skuNeedsAttention", () => {
  const peers = [
    { revenue: "100000", net_profit: "20000", margin_pct: "20" },
    { revenue: "80000", net_profit: "1000", margin_pct: "1.2" },
  ];

  it("flags high-revenue low-margin SKU", () => {
    expect(skuNeedsAttention(peers[1], peers)).toBe(true);
  });

  it("does not flag healthy high-revenue SKU", () => {
    expect(skuNeedsAttention(peers[0], peers)).toBe(false);
  });

  it("does not flag when profit and margin are gated/null", () => {
    expect(
      skuNeedsAttention({ revenue: "100000", net_profit: null, margin_pct: null }, peers),
    ).toBe(false);
  });

  it("flags high-revenue negative profit", () => {
    expect(
      skuNeedsAttention({ revenue: "90000", net_profit: "-500", margin_pct: null }, peers),
    ).toBe(true);
  });
});

describe("topSkuApiSortParam", () => {
  it("maps tabs to API sort values", () => {
    expect(topSkuApiSortParam("revenue")).toBe("revenue");
    expect(topSkuApiSortParam("profit")).toBe("profit");
    expect(topSkuApiSortParam("margin")).toBe("margin");
  });
});
