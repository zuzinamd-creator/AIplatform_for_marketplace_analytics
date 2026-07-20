import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import type { ProfitTrustContext } from "../state/profit-trust";
import { TrustChip } from "./trust-chip";

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

function renderChip(trustContext: ProfitTrustContext) {
  return render(
    <MemoryRouter>
      <TrustChip trustContext={trustContext} />
    </MemoryRouter>,
  );
}

describe("TrustChip", () => {
  afterEach(() => {
    cleanup();
  });

  it("renders trust label, coverage and SKU counts", () => {
    renderChip(ctx());

    expect(screen.getByTestId("trust-badge")).toBeTruthy();
    expect(screen.getByText("Оценка")).toBeTruthy();
    expect(screen.getByTestId("trust-chip-coverage").textContent).toMatch(/72/);
    expect(screen.getByTestId("trust-chip-sku").textContent).toBe("18 / 25 SKU");
  });

  it("shows CTA only when trust is not full", () => {
    renderChip(ctx({ trust: "partial" }));
    const cta = screen.getByTestId("trust-chip-cta");
    expect(cta.textContent).toMatch(/Уточнить/);
    expect(cta.getAttribute("href")).toBe("/app/costs");
  });

  it("hides CTA when trust is full", () => {
    renderChip(
      ctx({
        trust: "full",
        coveragePct: 100,
        coveredSkus: 25,
        totalSkus: 25,
        canShowMargin: true,
        canShowProfitAction: true,
      }),
    );

    expect(screen.getByText("Проверено")).toBeTruthy();
    expect(screen.queryByTestId("trust-chip-cta")).toBeNull();
  });

  it("omits coverage and SKU lines when values are unavailable", () => {
    renderChip(
      ctx({
        trust: "insufficient",
        coveragePct: null,
        coveredSkus: null,
        totalSkus: null,
      }),
    );

    expect(screen.getByText("Нет себестоимости")).toBeTruthy();
    expect(screen.queryByTestId("trust-chip-coverage")).toBeNull();
    expect(screen.queryByTestId("trust-chip-sku")).toBeNull();
    expect(screen.getByTestId("trust-chip-cta")).toBeTruthy();
  });
});
