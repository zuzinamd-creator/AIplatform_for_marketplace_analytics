import { describe, expect, it } from "vitest";

import { formatCompactRub } from "./format";

describe("formatCompactRub", () => {
  it("formats small values without suffix", () => {
    expect(formatCompactRub(0)).toBe("0");
    expect(formatCompactRub(999)).toBe("999");
  });

  it("formats thousands as тыс.", () => {
    expect(formatCompactRub(1250)).toBe("1.3 тыс.");
    expect(formatCompactRub(10_000)).toBe("10 тыс.");
  });

  it("formats millions as млн.", () => {
    expect(formatCompactRub(1_250_000)).toBe("1.25 млн.");
    expect(formatCompactRub(2_000_000)).toBe("2 млн.");
  });

  it("returns empty string for nullish", () => {
    expect(formatCompactRub(null)).toBe("");
    expect(formatCompactRub(undefined)).toBe("");
  });

  it("preserves negative sign", () => {
    expect(formatCompactRub(-1250)).toBe("−1.3 тыс.");
  });
});
