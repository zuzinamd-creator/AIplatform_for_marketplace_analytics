import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import type { ProfitTrustContext } from "../../state/profit-trust";
import { PrimaryAnswer } from "./PrimaryAnswer";

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

function renderBlock(
  props: Partial<{
    revenue: string;
    profit: string | null;
    trustCtx: ProfitTrustContext;
    isLoading: boolean;
  }> = {},
) {
  return render(
    <MemoryRouter>
      <PrimaryAnswer
        revenue={props.revenue ?? "1000"}
        profit={props.profit ?? "200"}
        trustCtx={props.trustCtx ?? ctx()}
        isLoading={props.isLoading}
      />
    </MemoryRouter>,
  );
}

describe("PrimaryAnswer", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders revenue and profit with existing formatters", () => {
    renderBlock({ revenue: "1500", profit: "300", trustCtx: ctx({ trust: "full" }) });

    expect(screen.getByTestId("primary-answer")).toBeTruthy();
    expect(screen.getByText("Выручка")).toBeTruthy();
    expect(screen.getByText("Чистая прибыль")).toBeTruthy();
    expect(screen.getByText(/1[\s\u00a0]?500/)).toBeTruthy();
    expect(screen.getByText(/300/)).toBeTruthy();
  });

  it("gates profit when trust is insufficient", () => {
    renderBlock({ profit: "300", trustCtx: ctx({ trust: "insufficient", canShowProfit: false }) });

    expect(screen.getByText("—")).toBeTruthy();
  });

  it("shows approximate profit when trust is partial", () => {
    renderBlock({ profit: "200", trustCtx: ctx({ trust: "partial" }) });

    expect(screen.getByText(/~.*200/)).toBeTruthy();
  });

  it("includes TrustChip", () => {
    renderBlock();

    expect(screen.getByTestId("trust-chip")).toBeTruthy();
  });

  it("shows loading placeholder", () => {
    renderBlock({ isLoading: true });

    expect(screen.getAllByText("…").length).toBeGreaterThanOrEqual(2);
  });
});
