import { describe, expect, it, afterEach } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { ProfitTrustBadge } from "./profit-trust-badge";

describe("ProfitTrustBadge", () => {
  afterEach(() => {
    cleanup();
  });
  it("renders full trust label with accessible description", () => {
    render(<ProfitTrustBadge trust="full" size="md" />);
    expect(screen.getByText("Проверено")).toBeTruthy();
    expect(screen.getByLabelText(/Себестоимость указана для всех продаваемых SKU/i)).toBeTruthy();
  });

  it("renders partial trust with coverage context in tooltip", () => {
    render(
      <ProfitTrustBadge
        trust="partial"
        trustContext={{ coveragePct: 72, coveredSkus: 18, totalSkus: 25 }}
      />,
    );
    expect(screen.getByText("Оценка")).toBeTruthy();
    expect(screen.getByLabelText(/Покрытие: 72 %/i)).toBeTruthy();
  });

  it("renders insufficient trust for margin metric", () => {
    render(<ProfitTrustBadge trust="insufficient" metric="margin" />);
    expect(screen.getByText("Нет себестоимости")).toBeTruthy();
    expect(screen.getByLabelText(/Маржа недоступна без себестоимости/i)).toBeTruthy();
  });

  it("supports icon-only mode", () => {
    render(<ProfitTrustBadge trust="partial" showLabel={false} tooltip={false} />);
    expect(screen.getByText("•")).toBeTruthy();
    expect(screen.queryByText("Оценка")).toBeNull();
  });
});
