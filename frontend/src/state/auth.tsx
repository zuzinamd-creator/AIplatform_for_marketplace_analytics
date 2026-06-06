import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { api, setAccessToken } from "../state/http";
import type { UserResponse } from "./types";

import { SESSION_EXPIRED_KEY, setUnauthorizedHandler } from "./session";

const TOKEN_KEY = "ma.accessToken";
export { SESSION_EXPIRED_KEY };

type AuthContextValue = {
  token: string | null;
  user: UserResponse | null;
  loading: boolean;
  signIn: (token: string) => Promise<void>;
  signOut: () => void;
  refreshMe: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider(props: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const refreshMe = async () => {
    if (!token) {
      setUser(null);
      return;
    }
    setLoading(true);
    try {
      const me = await api.auth.me();
      setUser(me);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setUnauthorizedHandler(() => {
      localStorage.removeItem(TOKEN_KEY);
      setAccessToken(null);
      setToken(null);
      setUser(null);
      sessionStorage.setItem(SESSION_EXPIRED_KEY, "1");
      const path = window.location.pathname;
      if (!path.startsWith("/login")) {
        window.location.assign("/login");
      }
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  const signIn = async (newToken: string) => {
    localStorage.setItem(TOKEN_KEY, newToken);
    setAccessToken(newToken);
    setToken(newToken);
    setLoading(true);
    try {
      const me = await api.auth.me();
      setUser(me);
    } finally {
      setLoading(false);
    }
  };

  const signOut = () => {
    localStorage.removeItem(TOKEN_KEY);
    setAccessToken(null);
    setToken(null);
    setUser(null);
  };

  const value = useMemo<AuthContextValue>(
    () => ({ token, user, loading, signIn, signOut, refreshMe }),
    [token, user, loading],
  );

  return <AuthContext.Provider value={value}>{props.children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("AuthProvider missing");
  return ctx;
}

export function RequireAuth(props: { children: React.ReactNode }) {
  const { token } = useAuth();
  const loc = useLocation();
  if (!token) return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  return <>{props.children}</>;
}

export function bootstrapTokenFromStorage() {
  const token = localStorage.getItem(TOKEN_KEY);
  setAccessToken(token);
  return token;
}

