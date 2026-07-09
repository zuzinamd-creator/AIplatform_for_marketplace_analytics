import { describe, expect, it } from "vitest";

import { USER_ROLE_PLATFORM_ADMIN, USER_ROLE_SELLER, isPlatformAdmin } from "./userRoles";
import type { UserResponse } from "./types";

function user(role: UserResponse["role"]): UserResponse {
  return {
    id: "user-1",
    email: "test@example.com",
    role,
    created_at: "2026-01-01T00:00:00Z",
  };
}

describe("isPlatformAdmin", () => {
  it("returns true only for platform_admin", () => {
    expect(isPlatformAdmin(user(USER_ROLE_PLATFORM_ADMIN))).toBe(true);
  });

  it("returns false for seller", () => {
    expect(isPlatformAdmin(user(USER_ROLE_SELLER))).toBe(false);
  });

  it("returns false for null/undefined", () => {
    expect(isPlatformAdmin(null)).toBe(false);
    expect(isPlatformAdmin(undefined)).toBe(false);
  });
});
