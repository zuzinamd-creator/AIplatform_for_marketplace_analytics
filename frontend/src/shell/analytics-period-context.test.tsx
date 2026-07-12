import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { AnalyticsPeriodProvider } from "./analytics-period-context";
import { AnalyticsShell } from "./AnalyticsShell";
import { savePeriodSelection, type PeriodSelection } from "../state/period";
import { usePagePeriod } from "../state/use-page-period";

const PERIOD_KEY = "ma.periodSelection.v1";

function TestConsumer() {
  return <div data-testid="period-consumer">period-consumer</div>;
}

function PeriodWriter({ sel }: { sel: PeriodSelection }) {
  const { setPeriodSel } = usePagePeriod();
  setPeriodSel(sel);
  return <div data-testid="period-writer" />;
}

describe("AnalyticsPeriodProvider", () => {
  beforeEach(() => {
    localStorage.clear();
    const seed: PeriodSelection = {
      preset: "14d",
      range: { start: "2026-05-01", end: "2026-05-14" },
      compareEnabled: false,
      comparePreset: "previous_period",
    };
    savePeriodSelection(seed);
  });

  afterEach(() => {
    cleanup();
    localStorage.clear();
  });

  it("wraps AnalyticsShell outlet with shared period context", () => {
    render(
      <MemoryRouter initialEntries={["/app/analytics"]}>
        <Routes>
          <Route path="/app/analytics" element={<AnalyticsShell />}>
            <Route index element={<TestConsumer />} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Аналитика" })).toBeTruthy();
    expect(screen.getByTestId("period-consumer")).toBeTruthy();
    expect(localStorage.getItem(PERIOD_KEY)).toContain("2026-05-01");
  });

  it("persists period updates through provider", () => {
    const updated: PeriodSelection = {
      preset: "custom",
      range: { start: "2026-06-01", end: "2026-06-30" },
      compareEnabled: true,
      comparePreset: "previous_period",
      compareRange: { start: "2026-05-01", end: "2026-05-31" },
    };

    render(
      <AnalyticsPeriodProvider>
        <PeriodWriter sel={updated} />
      </AnalyticsPeriodProvider>,
    );

    expect(screen.getByTestId("period-writer")).toBeTruthy();
    expect(localStorage.getItem(PERIOD_KEY)).toContain("2026-06-01");
    expect(localStorage.getItem(PERIOD_KEY)).toContain("2026-06-30");
  });
});
