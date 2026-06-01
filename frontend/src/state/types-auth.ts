export type Token = {
  access_token: string;
  token_type?: string;
};

export type UserCreate = {
  email: string;
  password: string;
};

export type UserResponse = {
  id: string;
  email: string;
  created_at: string;
};

