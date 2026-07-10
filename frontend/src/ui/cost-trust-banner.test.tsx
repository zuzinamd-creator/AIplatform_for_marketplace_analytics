import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { CostTrustBanner, CostTrustBannerMount } from "./cost-trust-banner";

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
  it("renders nothing while global feature flag is disabled", () => {
    const { container } = render(<CostTrustBannerMount />);
    expect(container.firstChild).toBeNull();
  });
});
