"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { API_BASE_URL } from "@/lib/config";
import { configureApiAuthBridge } from "@/lib/api/client";

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  tokenType: string; // "Bearer"
  expiresIn: number; // seconds
}

export interface AuthUser {
  id: string;
  email: string;
  createdAt: string;
}

export interface AuthState {
  ready: boolean;
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<string | null>;
}

const STORAGE_KEY = "badgers.auth.v1";

function safeJsonParse<T>(raw: string | null): T | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

type StoredAuth = {
  tokens: AuthTokens;
};

function loadStoredAuth(): StoredAuth | null {
  if (typeof window === "undefined") return null;
  return safeJsonParse<StoredAuth>(window.localStorage.getItem(STORAGE_KEY));
}

function saveStoredAuth(value: StoredAuth | null) {
  if (typeof window === "undefined") return;
  if (!value) window.localStorage.removeItem(STORAGE_KEY);
  else window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
}

async function readJsonOrThrow(res: Response): Promise<any> {
  const contentType = res.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) return await res.json();
  const text = await res.text();
  throw new Error(text || `HTTP ${res.status}`);
}

async function fetchJson<T>(path: string, init: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) {
    const body = await readJsonOrThrow(res).catch(() => null);
    const message =
      (body && (body.message || body.detail)) || `Request failed (${res.status})`;
    throw new Error(message);
  }
  return (await res.json()) as T;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();

  const [ready, setReady] = useState(false);
  const [tokens, setTokens] = useState<AuthTokens | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const refreshInFlight = useRef<Promise<string | null> | null>(null);

  const accessToken = tokens?.accessToken ?? null;
  const refreshToken = tokens?.refreshToken ?? null;
  const isAuthenticated = !!accessToken;

  useEffect(() => {
    const stored = loadStoredAuth();
    if (stored?.tokens?.accessToken) setTokens(stored.tokens);
    setReady(true);
  }, []);

  useEffect(() => {
    saveStoredAuth(tokens ? { tokens } : null);
  }, [tokens]);

  const fetchMe = useCallback(
    async (token: string) => {
      try {
        const res = await fetch(`${API_BASE_URL}/users/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) return null;
        return (await res.json()) as AuthUser;
      } catch {
        return null;
      }
    },
    [],
  );

  useEffect(() => {
    if (!accessToken) {
      setUser(null);
      return;
    }
    let cancelled = false;
    void (async () => {
      const me = await fetchMe(accessToken);
      if (cancelled) return;
      setUser(me);
    })();
    return () => {
      cancelled = true;
    };
  }, [accessToken, fetchMe]);

  const applyTokens = useCallback(async (next: AuthTokens) => {
    setTokens(next);
    const me = await fetchMe(next.accessToken);
    setUser(me);
  }, [fetchMe]);

  const login = useCallback(
    async (email: string, password: string) => {
      const next = await fetchJson<AuthTokens>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      await applyTokens(next);
    },
    [applyTokens],
  );

  const register = useCallback(
    async (email: string, password: string) => {
      const next = await fetchJson<AuthTokens>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      await applyTokens(next);
    },
    [applyTokens],
  );

  const refresh = useCallback(async (): Promise<string | null> => {
    if (!tokens?.refreshToken) return null;
    if (refreshInFlight.current) return refreshInFlight.current;

    refreshInFlight.current = (async () => {
      try {
        const next = await fetchJson<AuthTokens>("/auth/refresh", {
          method: "POST",
          body: JSON.stringify({ refreshToken: tokens.refreshToken }),
        });
        await applyTokens(next);
        return next.accessToken;
      } catch {
        setTokens(null);
        setUser(null);
        // If refresh fails, send user back to login. This is client-side only.
        router.replace("/login");
        return null;
      } finally {
        refreshInFlight.current = null;
      }
    })();

    return refreshInFlight.current;
  }, [applyTokens, router, tokens]);

  const logout = useCallback(async () => {
    const rt = tokens?.refreshToken;
    setTokens(null);
    setUser(null);
    saveStoredAuth(null);
    try {
      if (rt) {
        await fetchJson<void>("/auth/logout", {
          method: "POST",
          body: JSON.stringify({ refreshToken: rt }),
        });
      }
    } finally {
      router.replace("/login");
    }
  }, [router, tokens]);

  const value = useMemo<AuthState>(() => {
    return {
      ready,
      user,
      accessToken,
      refreshToken,
      isAuthenticated,
      login,
      register,
      logout,
      refresh,
    };
  }, [
    ready,
    user,
    accessToken,
    refreshToken,
    isAuthenticated,
    login,
    register,
    logout,
    refresh,
  ]);

  useEffect(() => {
    configureApiAuthBridge({
      getAccessToken: () => accessToken,
      refreshAccessToken: refresh,
    });
    return () => configureApiAuthBridge(null);
  }, [accessToken, refresh]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
