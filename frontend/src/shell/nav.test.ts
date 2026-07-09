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
  it("shows seller sections with account at the bottom", () => {
    const sections = buildNavSections(user(USER_ROLE_SELLER));
    const labels = sections.map((s) => s.label);
    expect(labels).toEqual(["Dashboard", "Analytics", "Reports", "AI", "Аккаунт"]);

    const analytics = sections.find((s) => s.id === "analytics");
    expect(analytics?.items.map((i) => i.to)).toContain("/app/analytics/weekly");

    const ai = sections.find((s) => s.id === "ai");
    expect(ai?.items.map((i) => i.to)).toEqual(["/app/ai/recommendations", "/app/ai/digest"]);
    expect(ai?.items.map((i) => i.label)).toEqual(["ИИ-помощник", "Сводка ИИ"]);

    const account = sections.find((s) => s.id === "account");
    expect(account?.items.map((i) => i.to)).toEqual(["/app/onboarding", "/app/settings", "/app/support"]);

    expect(sections.flatMap((s) => s.items).some((i) => i.to.startsWith("/app/admin"))).toBe(false);
  });

  it("shows admin operations and system for platform_admin without duplicate account section", () => {
    const sections = buildNavSections(user(USER_ROLE_PLATFORM_ADMIN));
    const labels = sections.map((s) => s.label);
    expect(labels).toEqual([
      "Dashboard",
      "Analytics",
      "Reports",
      "AI",
      "Аккаунт",
      "Администрирование",
      "Operations",
      "System",
    ]);

    const accountItems = sections.filter((s) => s.id === "account").flatMap((s) => s.items);
    expect(accountItems.map((i) => i.to)).toEqual(["/app/onboarding", "/app/settings", "/app/support"]);
    expect(sections.some((s) => s.id === "admin")).toBe(false);

    const administration = sections.find((s) => s.id === "administration");
    expect(administration?.items.map((i) => i.label)).toEqual(["Пользователи", "Приглашения"]);
    expect(administration?.items.map((i) => i.to)).toEqual(["/app/admin/users", "/app/admin/invites"]);
    expect(sections.find((s) => s.id === "operations")?.items.length).toBeGreaterThan(0);
    expect(sections.find((s) => s.id === "system")?.items.length).toBeGreaterThan(0);
  });
});
