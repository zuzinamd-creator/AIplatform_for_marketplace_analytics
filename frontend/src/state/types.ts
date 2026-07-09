import type { UserRole } from "./userRoles";

export type UserResponse = {
  id: string;
  email: string;
  full_name?: string | null;
  is_active?: boolean;
  role: UserRole;
  created_at: string;
};
