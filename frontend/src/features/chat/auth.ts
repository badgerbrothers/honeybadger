const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "/api").replace(/\/$/, "");
const AUTH_STORAGE_KEY = "badgers.auth.tokens.v1";
const ACCESS_SKEW_MS = 15_000;

interface AuthApiResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
}

interface StoredAuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
}

let tokenRefreshInFlight: Promise<string> | null = null;

function loadTokens(): StoredAuthTokens | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as StoredAuthTokens;
    if (!parsed.accessToken || !parsed.refreshToken || !parsed.expiresAt) return null;
    return parsed;
  } catch {
    return null;
  }
}

function saveTokens(payload: AuthApiResponse): StoredAuthTokens {
  const tokens: StoredAuthTokens = {
    accessToken: payload.accessToken,
    refreshToken: payload.refreshToken,
    expiresAt: Date.now() + payload.expiresIn * 1000,
  };
  if (typeof window !== "undefined") {
    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(tokens));
  }
  return tokens;
}

function clearTokens() {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
  }
}

function hasValidAccessToken(tokens: StoredAuthTokens): boolean {
  return tokens.expiresAt - ACCESS_SKEW_MS > Date.now();
}

async function callAuthEndpoint(
  path: string,
  body: Record<string, unknown>,
): Promise<AuthApiResponse> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const fallback = `${response.status} ${response.statusText}`;
    let detail = fallback;
    try {
      const payload = (await response.json()) as { detail?: string | { message?: string } };
      detail = payload?.detail && typeof payload.detail === "object" ? payload.detail.message || fallback : String(payload?.detail || fallback);
    } catch {
      // ignore parse error
    }
    throw new Error(detail);
  }
  return (await response.json()) as AuthApiResponse;
}

async function loginOrRegister(): Promise<string> {
  const email = process.env.NEXT_PUBLIC_AUTH_EMAIL || "demo@badgers.local";
  const password = process.env.NEXT_PUBLIC_AUTH_PASSWORD || "badgers-demo-password";

  try {
    const loginTokens = await callAuthEndpoint("/auth/login", { email, password });
    return saveTokens(loginTokens).accessToken;
  } catch {
    const registerTokens = await callAuthEndpoint("/auth/register", { email, password });
    return saveTokens(registerTokens).accessToken;
  }
}

async function refreshAccessToken(refreshToken: string): Promise<string> {
  try {
    const refreshed = await callAuthEndpoint("/auth/refresh", { refreshToken });
    return saveTokens(refreshed).accessToken;
  } catch {
    clearTokens();
    throw new Error("Session expired");
  }
}

async function ensureAccessToken(): Promise<string> {
  const current = loadTokens();
  if (current && hasValidAccessToken(current)) return current.accessToken;
  if (current?.refreshToken) {
    return refreshAccessToken(current.refreshToken);
  }
  return loginOrRegister();
}

async function withRefreshLock(factory: () => Promise<string>): Promise<string> {
  if (!tokenRefreshInFlight) {
    tokenRefreshInFlight = factory().finally(() => {
      tokenRefreshInFlight = null;
    });
  }
  return tokenRefreshInFlight;
}

export async function authorizedFetch(path: string, init?: RequestInit): Promise<Response> {
  const token = await withRefreshLock(ensureAccessToken);
  const firstResponse = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      Authorization: `Bearer ${token}`,
    },
  });

  if (firstResponse.status !== 401) return firstResponse;
  const stored = loadTokens();
  if (!stored?.refreshToken) return firstResponse;

  const refreshedToken = await withRefreshLock(() => refreshAccessToken(stored.refreshToken));
  return fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
      Authorization: `Bearer ${refreshedToken}`,
    },
  });
}
