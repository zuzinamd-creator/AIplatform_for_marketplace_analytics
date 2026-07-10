import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { CostCoverageIndicator } from "./cost-coverage-indicator";

function renderIndicator(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe("CostCoverageIndicator", () => {
  it("renders pill variant with coverage summary", () => {
    renderIndicator(
      <CostCoverageIndicator coveredSkus={8} totalSkus={10} coveragePct="80" variant="pill" />,
    );
    expect(screen.getByText(/Себестоимость 80 %/)).toBeTruthy();
    expect(screen.getByLabelText(/8 \/ 10 SKU/i)).toBeTruthy();
  });

  it("renders bar variant with progressbar semantics", () => {
    renderIndicator(
      <CostCoverageIndicator coveredSkus={5} totalSkus={5} coveragePct={100} variant="bar" />,
    );
    expect(screen.getByRole("progressbar", { name: /Покрытие 100 %/ })).toBeTruthy();
  });

  it("renders ring variant with CTA link", () => {
    renderIndicator(
      <CostCoverageIndicator
        coveredSkus={2}
        totalSkus={10}
        coveragePct="20"
        variant="ring"
        showCta
      />,
    );
    expect(screen.getByRole("link", { name: /Загрузить себестоимость/i }).getAttribute("href")).toBe(
      "/app/costs",
    );
  });

  it("calls onClick handler for CTA when provided", () => {
    const onClick = vi.fn();
    renderIndicator(
      <CostCoverageIndicator
        coveredSkus={0}
        totalSkus={3}
        coveragePct="0"
        variant="pill"
        showCta
        onClick={onClick}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Загрузить себестоимость/i }));
    expect(onClick).toHaveBeenCalledOnce();
  });
});
