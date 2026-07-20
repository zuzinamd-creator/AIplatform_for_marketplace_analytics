import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { FirstRunChecklist } from "./first-run-checklist";

const isFirstRunChecklistDismissed = vi.fn();
const dismissFirstRunChecklist = vi.fn();
const isOnboardingDone = vi.fn();

vi.mock("../state/first-run", () => ({
  isFirstRunChecklistDismissed: () => isFirstRunChecklistDismissed(),
  dismissFirstRunChecklist: () => dismissFirstRunChecklist(),
}));

vi.mock("../state/onboarding", () => ({
  isOnboardingDone: () => isOnboardingDone(),
}));

function renderChecklist() {
  return render(
    <MemoryRouter>
      <FirstRunChecklist />
    </MemoryRouter>,
  );
}

describe("FirstRunChecklist", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders when onboarding is incomplete and checklist not dismissed", () => {
    isFirstRunChecklistDismissed.mockReturnValue(false);
    isOnboardingDone.mockReturnValue(false);
    renderChecklist();

    expect(screen.getByText(/Первый запуск: чек‑лист продавца/i)).toBeTruthy();
  });

  it("hides when onboarding is done", () => {
    isFirstRunChecklistDismissed.mockReturnValue(false);
    isOnboardingDone.mockReturnValue(true);
    const { container } = renderChecklist();

    expect(container.firstChild).toBeNull();
  });

  it("hides when checklist was dismissed", () => {
    isFirstRunChecklistDismissed.mockReturnValue(true);
    isOnboardingDone.mockReturnValue(false);
    const { container } = renderChecklist();

    expect(container.firstChild).toBeNull();
  });

  it("persists dismiss via first-run storage helper", () => {
    isFirstRunChecklistDismissed.mockReturnValue(false);
    isOnboardingDone.mockReturnValue(false);
    renderChecklist();

    fireEvent.click(screen.getByRole("button", { name: /Скрыть чек-лист/i }));
    expect(dismissFirstRunChecklist).toHaveBeenCalledTimes(1);
  });
});
