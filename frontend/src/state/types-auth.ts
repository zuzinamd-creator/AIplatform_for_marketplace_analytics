export type Token = {
  access_token: string;
  token_type?: string;
};

export type UserCreate = {
  email: string;
  password: string;
  full_name?: string | null;
  invite_token?: string;
};

export type InviteValidateResponse = {
  valid: boolean;
  email?: string | null;
  expires_at?: string | null;
};

export type { UserResponse } from "./types";

export type RegistrationStatusResponse = {
  available: boolean;
};
