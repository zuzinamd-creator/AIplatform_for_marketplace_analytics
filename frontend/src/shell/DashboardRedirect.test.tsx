import { describe, expect, it, afterEach } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { DashboardRedirect } from "./DashboardRedirect";

describe("DashboardRedirect", () => {
  afterEach(() => {
    cleanup();
  });

  it("redirects /app/dashboard to /app/analytics preserving query string", async () => {
    render(
      <MemoryRouter initialEntries={["/app/dashboard?foo=bar"]}>
        <Routes>
          <Route path="/app/dashboard" element={<DashboardRedirect />} />
          <Route path="/app/analytics" element={<div>analytics-hub</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("analytics-hub")).toBeTruthy();
  });
});
