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

export type InviteStatus = "pending" | "used" | "expired" | "revoked";

export type AdminInviteListItem = {
  id: string;
  email: string;
  role: "seller" | "platform_admin";
  status: InviteStatus;
  expires_at: string;
  created_at: string;
};

export type PaginatedAdminInvitesResponse = {
  items: AdminInviteListItem[];
  page: {
    total: number;
    skip: number;
    limit: number;
  };
};

export type AdminInviteCreateResponse = {
  email: string;
  role: "seller";
  status: InviteStatus;
  expires_at: string;
  created_at: string;
  invite_link: string;
};
