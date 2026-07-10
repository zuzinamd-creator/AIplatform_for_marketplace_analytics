import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { AiTrustPanel } from "./ai-trust-panel";

describe("AiTrustPanel", () => {
  it("renders cost trust badge when costTrust prop is provided", () => {
    render(
      <AiTrustPanel
        trust={{ advisory_only: true, confidence_explanation: "Test" }}
        costTrust={{ trust: "partial", coveragePct: 72, coveredSkus: 18, totalSkus: 25 }}
      />,
    );
    expect(screen.getByLabelText(/Прибыль рассчитана не для всех SKU/i)).toBeTruthy();
  });
});
