export type AdminUserListItem = {
  email: string;
  role: "seller" | "platform_admin";
  is_active: boolean;
  created_at: string;
};

export type PaginatedAdminUsersResponse = {
  items: AdminUserListItem[];
  page: {
    total: number;
    skip: number;
    limit: number;
  };
};
