import { describe, expect, it } from "vitest";
import { renderHook } from "@testing-library/react";

import { formatRub } from "../utils/format";
import {
  deriveProfitTrustContext,
  formatDeltaWithTrust,
  formatProfitValue,
  normalizeProfitTrust,
  useProfitTrust,
} from "./profit-trust";

describe("normalizeProfitTrust", () => {
  it("passes through known API trust levels", () => {
    expect(normalizeProfitTrust("full")).toBe("full");
    expect(normalizeProfitTrust("partial")).toBe("partial");
    expect(normalizeProfitTrust("insufficient")).toBe("insufficient");
  });

  it("defaults unknown values to insufficient", () => {
    expect(normalizeProfitTrust(null)).toBe("insufficient");
    expect(normalizeProfitTrust("unknown")).toBe("insufficient");
  });
});

describe("deriveProfitTrustContext", () => {
  it("reads trust from integrity only and never recalculates from coverage", () => {
    const ctx = deriveProfitTrustContext(
      { warnings: [], profit_metrics_trust: "partial", sku_cost_coverage_pct: "100" },
      { sku_cost_coverage_pct: "100", covered_skus: 10, total_skus: 10 } as never,
    );

    expect(ctx.trust).toBe("partial");
    expect(ctx.coveragePct).toBe(100);
    expect(ctx.canShowProfit).toBe(true);
    expect(ctx.canShowMargin).toBe(false);
    expect(ctx.canShowProfitAction).toBe(false);
  });

  it("marks insufficient trust as non-displayable for profit KPIs", () => {
    const ctx = deriveProfitTrustContext(
      { warnings: [], profit_metrics_trust: "insufficient" },
      null,
    );

    expect(ctx.canShowProfit).toBe(false);
    expect(ctx.canShowMargin).toBe(false);
    expect(ctx.canShowProfitAction).toBe(false);
  });

  it("prefers cost coverage response for SKU counts", () => {
    const ctx = deriveProfitTrustContext(
      { warnings: [], profit_metrics_trust: "full", sku_cost_coverage_pct: "95" },
      {
        sku_cost_coverage_pct: "100",
        covered_skus: 8,
        total_skus: 8,
        missing_skus: ["SKU-1"],
      } as never,
    );

    expect(ctx.trust).toBe("full");
    expect(ctx.coveredSkus).toBe(8);
    expect(ctx.totalSkus).toBe(8);
    expect(ctx.missingSkus).toEqual(["SKU-1"]);
  });
});

describe("useProfitTrust", () => {
  it("memoizes derived context", () => {
    const integrity = { warnings: [], profit_metrics_trust: "full" as const };
    const { result, rerender } = renderHook(
      ({ i }) => useProfitTrust(i, null),
      { initialProps: { i: integrity } },
    );

    expect(result.current.trust).toBe("full");
    rerender({ i: integrity });
    expect(result.current.canShowMargin).toBe(true);
  });
});

describe("formatProfitValue", () => {
  it("formats full trust values without approximation prefix", () => {
    expect(formatProfitValue("1234.5", "full")).toBe(formatRub("1234.5"));
  });

  it("prefixes partial trust values with tilde", () => {
    expect(formatProfitValue("1234.5", "partial")).toBe(`~${formatRub("1234.5")}`);
  });

  it("hides profit for insufficient trust", () => {
    expect(formatProfitValue("1234.5", "insufficient")).toBe("—");
  });
});

describe("formatDeltaWithTrust", () => {
  it("shows signed rub delta for partial trust with approximation", () => {
    expect(formatDeltaWithTrust("150", "partial", "rub")).toBe("~+150 ₽");
    expect(formatDeltaWithTrust("-50", "partial", "rub")).toBe("~-50 ₽");
  });

  it("blocks deltas for insufficient trust", () => {
    expect(formatDeltaWithTrust("10", "insufficient", "pct")).toBe("н/д");
  });

  it("shows full-trust pct delta", () => {
    expect(formatDeltaWithTrust("2.5", "full", "pct")).toBe("+2,5 %");
  });
});
