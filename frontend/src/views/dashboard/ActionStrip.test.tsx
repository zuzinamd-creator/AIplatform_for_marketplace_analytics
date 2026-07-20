import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";

import { ActionStrip } from "./ActionStrip";
import type { ActionCard } from "./action-strip";

const scrollIntoView = vi.fn();

function LocationProbe() {
  const loc = useLocation();
  return <div data-testid="loc">{`${loc.pathname}${loc.hash}`}</div>;
}

describe("ActionStrip CTA hash scroll", () => {
  beforeEach(() => {
    scrollIntoView.mockReset();
    document.body.innerHTML = "";
    const target = document.createElement("div");
    target.id = "dashboard-cost-structure";
    target.scrollIntoView = scrollIntoView;
    document.body.appendChild(target);
  });

  afterEach(() => {
    cleanup();
  });

  it("scrolls to cost section when Смотреть расходы is clicked on the same route", async () => {
    const cards: ActionCard[] = [
      {
        id: "signal-cost",
        title: "Структура расходов",
        body: "Комиссия WB составляет 46% всех расходов за период.",
        ctaLabel: "Смотреть расходы",
        ctaHref: "/app/analytics#dashboard-cost-structure",
      },
    ];

    render(
      <MemoryRouter initialEntries={["/app/analytics"]}>
        <Routes>
          <Route
            path="/app/analytics"
            element={
              <>
                <LocationProbe />
                <ActionStrip cards={cards} />
              </>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByRole("link", { name: "Смотреть расходы" }));
    await vi.waitFor(() => {
      expect(scrollIntoView).toHaveBeenCalled();
    });
    expect(screen.getByTestId("loc").textContent).toBe("/app/analytics#dashboard-cost-structure");
  });
});
