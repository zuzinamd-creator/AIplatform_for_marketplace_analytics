import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { CostTrustBanner, CostTrustBannerMount } from "./cost-trust-banner";

vi.mock("../state/use-cost-trust-shell", () => ({
  useCostTrustShellData: () => ({
    trust: "partial" as const,
    coveragePct: 72,
    coveredSkus: 18,
    totalSkus: 25,
    missingSkus: ["SKU-1"],
    canShowProfit: true,
    canShowMargin: false,
    canShowProfitAction: false,
  }),
}));

function renderBanner(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("CostTrustBanner", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  afterEach(() => {
    cleanup();
  });

  it("does not render for full trust", () => {
    const { container } = renderBanner(<CostTrustBanner trust="full" />);
    expect(container.firstChild).toBeNull();
  });

  it("renders partial trust inline banner with CTA links", () => {
    renderBanner(
      <CostTrustBanner
        trust="partial"
        variant="inline"
        coveragePct="72"
        coveredSkus={18}
        totalSkus={25}
        dismissible={false}
      />,
    );

    expect(screen.getByRole("status")).toBeTruthy();
    expect(screen.getByText(/Себестоимость: 72 %/)).toBeTruthy();
    expect(screen.getByRole("link", { name: /Загрузить себестоимость/i }).getAttribute("href")).toBe(
      "/app/costs",
    );
    expect(screen.getByRole("link", { name: /Покрытие себестоимости/i }).getAttribute("href")).toBe(
      "/app/finance/cost-coverage",
    );
  });

  it("persists dismiss state in session storage", () => {
    renderBanner(
      <CostTrustBanner trust="insufficient" storageKey="test-dismiss" variant="compact" />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Скрыть предупреждение/i }));
    expect(sessionStorage.getItem("ma.costTrustBanner.dismissed.test-dismiss")).toBe("1");
  });

  it("respects existing dismiss flag on mount", () => {
    sessionStorage.setItem("ma.costTrustBanner.dismissed.test-existing", "1");
    const { container } = renderBanner(
      <CostTrustBanner trust="partial" storageKey="test-existing" />,
    );
    expect(container.firstChild).toBeNull();
  });
});

describe("CostTrustBannerMount", () => {
  it("renders global banner when feature flag is enabled", () => {
    render(
      <MemoryRouter>
        <CostTrustBannerMount />
      </MemoryRouter>,
    );
    expect(screen.getByRole("status")).toBeTruthy();
    expect(screen.getByText(/Оценка/)).toBeTruthy();
  });
});
