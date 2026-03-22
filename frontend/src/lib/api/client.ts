import { API_BASE_URL } from "@/lib/config";

type ResponseType = "json" | "blob" | "text";

type AuthBridge = {
  getAccessToken: () => string | null;
  refreshAccessToken: () => Promise<string | null>;
};

let authBridge: AuthBridge | null = null;

export function configureApiAuthBridge(bridge: AuthBridge | null) {
  authBridge = bridge;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(message: string, status: number, detail: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

function toAbsoluteUrl(path: string) {
  if (/^https?:\/\//i.test(path)) return path;
  if (path.startsWith("/")) return `${API_BASE_URL}${path}`;
  return `${API_BASE_URL}/${path}`;
}

async function parseError(response: Response): Promise<ApiError> {
  const contentType = response.headers.get("content-type") ?? "";
  let detail: unknown = null;
  if (contentType.includes("application/json")) {
    try {
      detail = await response.json();
    } catch {
      detail = null;
    }
  } else {
    try {
      detail = await response.text();
    } catch {
      detail = null;
    }
  }

  const message =
    (typeof detail === "object" &&
      detail &&
      ("message" in detail || "detail" in detail) &&
      String((detail as any).message ?? (detail as any).detail)) ||
    (typeof detail === "string" && detail) ||
    `Request failed (${response.status})`;

  return new ApiError(message, response.status, detail);
}

interface ApiFetchOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
  responseType?: ResponseType;
  skipAuth?: boolean;
}

async function executeFetch(
  path: string,
  {
    method = "GET",
    body,
    headers = {},
    responseType = "json",
    skipAuth = false,
  }: ApiFetchOptions,
) {
  const requestHeaders = new Headers(headers);

  const token = !skipAuth ? authBridge?.getAccessToken() : null;
  if (token) requestHeaders.set("Authorization", `Bearer ${token}`);

  const init: RequestInit = { method, headers: requestHeaders };

  if (body !== undefined && body !== null) {
    if (body instanceof FormData) {
      init.body = body;
    } else if (typeof body === "string") {
      requestHeaders.set("content-type", "application/json");
      init.body = body;
    } else {
      requestHeaders.set("content-type", "application/json");
      init.body = JSON.stringify(body);
    }
  }

  return fetch(toAbsoluteUrl(path), init);
}

export async function apiFetch<T = unknown>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  let response = await executeFetch(path, options);

  if (response.status === 401 && !options.skipAuth && authBridge) {
    const nextAccessToken = await authBridge.refreshAccessToken();
    if (nextAccessToken) {
      response = await executeFetch(path, options);
    }
  }

  if (!response.ok) throw await parseError(response);

  const responseType = options.responseType ?? "json";
  if (response.status === 204) return undefined as T;

  if (responseType === "blob") return (await response.blob()) as T;
  if (responseType === "text") return (await response.text()) as T;

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    const text = await response.text();
    return text as T;
  }
  return (await response.json()) as T;
}

