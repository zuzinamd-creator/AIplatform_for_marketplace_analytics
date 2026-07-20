import { describe, expect, it, vi, afterEach } from "vitest";

import { scrollToHashTarget, splitPathAndHash } from "./hash-scroll";

describe("splitPathAndHash", () => {
  it("splits analytics cost anchor", () => {
    expect(splitPathAndHash("/app/analytics#dashboard-cost-structure")).toEqual({
      pathname: "/app/analytics",
      hash: "#dashboard-cost-structure",
    });
  });

  it("handles href without hash", () => {
    expect(splitPathAndHash("/app/today")).toEqual({ pathname: "/app/today", hash: "" });
  });
});

describe("scrollToHashTarget", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("scrolls to element by hash id", () => {
    const el = document.createElement("div");
    el.id = "dashboard-cost-structure";
    el.scrollIntoView = vi.fn();
    document.body.appendChild(el);

    expect(scrollToHashTarget("#dashboard-cost-structure")).toBe(true);
    expect(el.scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth", block: "start" });
  });

  it("returns false when target is missing", () => {
    expect(scrollToHashTarget("#missing")).toBe(false);
  });
});
