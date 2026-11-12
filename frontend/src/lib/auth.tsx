"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { api, refreshSession, sessionLogin, sessionLogout } from "./api";
import type { User } from "./types";

type AuthValue = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  reloadUser: () => Promise<void>;
  setUser: (user: User) => void;
};

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUserState] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const reloadUser = useCallback(async () => {
    try {
      setUserState(await api<User>("/api/v1/users/me/"));
    } catch {
      setUserState(null);
    }
  }, []);

  // On every page load: trade the refresh cookie for an access token, then load the profile
  useEffect(() => {
    let active = true;
    (async () => {
      const token = await refreshSession();
      if (token) await reloadUser();
      if (active) setLoading(false);
    })();
    return () => {
      active = false;
    };
  }, [reloadUser]);

  const login = useCallback(
    async (email: string, password: string) => {
      await sessionLogin(email, password);
      await reloadUser();
    },
    [reloadUser],
  );

  const logout = useCallback(async () => {
    await sessionLogout();
    setUserState(null);
  }, []);

  const value = useMemo<AuthValue>(
    () => ({ user, loading, login, logout, reloadUser, setUser: setUserState }),
    [user, loading, login, logout, reloadUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}
