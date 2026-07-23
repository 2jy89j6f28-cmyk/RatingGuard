"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";

/* ═══════════════════════════════════════════════════════════════
   Auth Context
   ═══════════════════════════════════════════════════════════════ */

interface AuthState {
  isAuthenticated: boolean;
  username: string | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

const TOKEN_KEY = "ratingguard_token";
const USERNAME_KEY = "ratingguard_username";

async function apiAuth(endpoint: string, username: string, password: string) {
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error((data as { detail?: string }).detail || `请求失败 (${res.status})`);
  }
  return res.json() as Promise<{ access_token: string; token_type: string; username: string }>;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);

  // 页面加载时从 localStorage 恢复 token
  useEffect(() => {
    const savedToken = localStorage.getItem(TOKEN_KEY);
    const savedUsername = localStorage.getItem(USERNAME_KEY);
    if (savedToken && savedUsername) {
      setToken(savedToken);
      setUsername(savedUsername);
    }
  }, []);

  const login = useCallback(async (uname: string, pwd: string) => {
    const result = await apiAuth("/api/auth/login", uname, pwd);
    localStorage.setItem(TOKEN_KEY, result.access_token);
    localStorage.setItem(USERNAME_KEY, result.username);
    setToken(result.access_token);
    setUsername(result.username);
  }, []);

  const register = useCallback(async (uname: string, pwd: string) => {
    const result = await apiAuth("/api/auth/register", uname, pwd);
    localStorage.setItem(TOKEN_KEY, result.access_token);
    localStorage.setItem(USERNAME_KEY, result.username);
    setToken(result.access_token);
    setUsername(result.username);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USERNAME_KEY);
    setToken(null);
    setUsername(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: token !== null,
        username,
        token,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
