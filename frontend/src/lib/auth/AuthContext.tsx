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

function defaultErrorMessage(status: number): string {
  switch (status) {
    case 400:
      return "Request parameters are invalid.";
    case 401:
      return "Invalid email or password.";
    case 403:
      return "You do not have permission to perform this action.";
    case 404:
      return "Requested resource was not found.";
    case 409:
      return "This email is already registered.";
    case 422:
      return "Validation failed. Please check your input.";
    case 500:
      return "Server error. Please try again later.";
    default:
      return `Request failed (${status})`;
  }
}

function defaultErrorMessageByCode(code: string): string | null {
  switch (code) {
    case "AUTH_INVALID_CREDENTIALS":
      return "Invalid email or password.";
    case "AUTH_EMAIL_ALREADY_REGISTERED":
      return "This email is already registered.";
    case "AUTH_INVALID_REFRESH_TOKEN":
    case "AUTH_INVALID_TOKEN":
    case "AUTH_INVALID_TOKEN_TYPE":
      return "Your session is invalid or expired. Please log in again.";
    case "VALIDATION_ERROR":
      return "Validation failed. Please check your input.";
    case "INVALID_REQUEST_BODY":
      return "Request format is invalid.";
    default:
      return null;
  }
}

async function readErrorPayload(
  res: Response,
): Promise<{ message: string; code?: string }> {
  const contentType = res.headers.get("content-type") ?? "";
  let code: string | undefined;
  try {
    if (contentType.includes("application/json")) {
      const body = (await res.json()) as
        | { code?: string; message?: string; detail?: string; error?: string }
        | null;
      code = body?.code?.trim() || undefined;
      const message = body?.message || body?.detail || body?.error;
      if (message && message.trim()) return { message, code };
    } else {
      const text = await res.text();
      if (text.trim()) return { message: text.trim(), code };
    }
  } catch {
    // ignore parse errors and fallback to status mapping
  }
  return {
    message:
      (code ? defaultErrorMessageByCode(code) : null) ??
      defaultErrorMessage(res.status),
    code,
  };
}

async function fetchJson<T>(path: string, init: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "content-type": "application/json",
        ...(init.headers ?? {}),
      },
    });
  } catch {
    throw new Error(
      "Unable to connect to the API gateway. Check gateway startup and CORS settings.",
    );
  }
  if (!res.ok) {
    const { message, code } = await readErrorPayload(res);
    const fallbackByCode = code ? defaultErrorMessageByCode(code) : null;
    throw new Error(fallbackByCode ?? message);
  }
  if (res.status === 204) return undefined as T;
  const contentType = res.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return (await res.json()) as T;
  }
  return (await res.text()) as T;
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
