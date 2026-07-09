import type { UserResponse } from "./types";

export const USER_ROLE_SELLER = "seller" as const;
export const USER_ROLE_PLATFORM_ADMIN = "platform_admin" as const;

export type UserRole = typeof USER_ROLE_SELLER | typeof USER_ROLE_PLATFORM_ADMIN;

export function isPlatformAdmin(user: UserResponse | null | undefined): boolean {
  return user?.role === USER_ROLE_PLATFORM_ADMIN;
}
