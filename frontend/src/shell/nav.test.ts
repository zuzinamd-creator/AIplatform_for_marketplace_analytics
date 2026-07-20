import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { buildNavSections, sellerNavTargets } from "./nav";
import { setOnboardingDone } from "../state/onboarding";
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
  beforeEach(() => {
    localStorage.clear();
    setOnboardingDone(false);
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("shows seller sections per F1.6 Section 5", () => {
    const sections = buildNavSections(user(USER_ROLE_SELLER));
    const labels = sections.map((s) => s.label);
    expect(labels).toEqual(["Обзор", "Аналитика", "Данные", "Действия", "Аккаунт"]);

    const overview = sections.find((s) => s.id === "overview");
    expect(overview?.items.map((i) => i.to)).toEqual(["/app/analytics", "/app/today"]);
    expect(overview?.items.map((i) => i.label)).toEqual(["Панель", "Сегодня"]);

    const analytics = sections.find((s) => s.id === "analytics");
    expect(analytics?.items.map((i) => i.to)).toEqual([
      "/app/analytics/weekly",
      "/app/analytics/economics",
      "/app/economics/inventory",
      "/app/finance/reconciliation",
    ]);
    expect(analytics?.items.map((i) => i.label)).toEqual([
      "Сравнение периодов",
      "Экономика SKU",
      "Склад и оборот",
      "Сверка выплат",
    ]);
    expect(analytics?.items.some((i) => i.to === "/app/analytics")).toBe(false);

    const data = sections.find((s) => s.id === "data");
    expect(data?.items.map((i) => i.to)).toEqual([
      "/app/reports/upload",
      "/app/reports",
      "/app/costs",
      "/app/analytics/cost-coverage",
    ]);
    expect(data?.items.map((i) => i.label)).toEqual([
      "Загрузка отчёта",
      "Отчёты",
      "Себестоимость",
      "Покрытие себестоимости",
    ]);

    const actions = sections.find((s) => s.id === "actions");
    expect(actions?.items.map((i) => i.to)).toEqual(["/app/ai/recommendations", "/app/ai/digest"]);
    expect(actions?.items.map((i) => i.label)).toEqual(["ИИ-помощник", "Сводка ИИ"]);

    const account = sections.find((s) => s.id === "account");
    expect(account?.items.map((i) => i.to)).toEqual([
      "/app/onboarding",
      "/app/settings",
      "/app/support",
    ]);

    expect(sections.flatMap((s) => s.items).some((i) => i.to.startsWith("/app/admin"))).toBe(false);
  });

  it("hides onboarding nav item when onboarding is complete", () => {
    setOnboardingDone(true);
    const sections = buildNavSections(user(USER_ROLE_SELLER));
    const account = sections.find((s) => s.id === "account");
    expect(account?.items.map((i) => i.to)).toEqual(["/app/settings", "/app/support"]);
  });

  it("has no duplicate canonical URLs in seller navigation", () => {
    const targets = sellerNavTargets();
    expect(new Set(targets).size).toBe(targets.length);
  });

  it("shows admin operations and system for platform_admin without duplicate account section", () => {
    const sections = buildNavSections(user(USER_ROLE_PLATFORM_ADMIN));
    const labels = sections.map((s) => s.label);
    expect(labels).toEqual([
      "Обзор",
      "Аналитика",
      "Данные",
      "Действия",
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
