import { describe, expect, it } from "vitest";

import { buildNavSections } from "./nav";
import { USER_ROLE_PLATFORM_ADMIN, USER_ROLE_SELLER } from "../state/userRoles";
import type { UserResponse } from "../state/types";

function user(role: UserResponse["role"]): UserResponse {
  return {
    id: "user-1",
    email: "test@example.com",
    role,
    created_at: "2026-01-01T00:00:00Z",
  };
}

describe("buildNavSections", () => {
  it("shows seller sections only for seller", () => {
    const sections = buildNavSections(user(USER_ROLE_SELLER));
    const labels = sections.map((s) => s.label);
    expect(labels).toEqual(["Dashboard", "Analytics", "Reports", "AI"]);
    expect(sections.flatMap((s) => s.items).some((i) => i.to.startsWith("/app/admin"))).toBe(false);
  });

  it("shows admin operations and system for platform_admin", () => {
    const sections = buildNavSections(user(USER_ROLE_PLATFORM_ADMIN));
    const labels = sections.map((s) => s.label);
    expect(labels).toEqual([
      "Dashboard",
      "Analytics",
      "Reports",
      "AI",
      "Администрирование",
      "Admin",
      "Operations",
      "System",
    ]);
    expect(sections.find((s) => s.id === "administration")?.items[0]?.to).toBe("/app/admin/users");
    expect(sections.find((s) => s.id === "operations")?.items.length).toBeGreaterThan(0);
    expect(sections.find((s) => s.id === "system")?.items.length).toBeGreaterThan(0);
  });
});
