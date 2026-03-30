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

function isLoopbackHost(hostname: string): boolean {
  const host = hostname.trim().toLowerCase();
  return host === "localhost" || host === "127.0.0.1" || host === "::1";
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
  const url = toAbsoluteUrl(path);
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

  try {
  return await fetch(url, init);
  } catch (error) {
    if (typeof window !== "undefined") {
      try {
        const parsed = new URL(url);
        const pageHost = window.location.hostname;
        if (isLoopbackHost(parsed.hostname) && pageHost && !isLoopbackHost(pageHost)) {
          const fallback = `${window.location.protocol}//${pageHost}${parsed.pathname}${parsed.search}`;
          return await fetch(fallback, init);
        }
      } catch {
        // keep original network error
      }
    }
    throw new ApiError(
      `Network error calling ${url}. Check that API gateway is reachable at ${API_BASE_URL}.`,
      0,
      error,
    );
  }
}

interface ApiUploadOptions {
  headers?: Record<string, string>;
  skipAuth?: boolean;
  onUploadProgress?: (loaded: number, total: number) => void;
}

function toApiError(status: number, detail: unknown): ApiError {
  const message =
    (typeof detail === "object" &&
      detail &&
      ("message" in detail || "detail" in detail) &&
      String((detail as any).message ?? (detail as any).detail)) ||
    (typeof detail === "string" && detail) ||
    `Request failed (${status})`;
  return new ApiError(message, status, detail);
}

function parseXhrErrorPayload(contentType: string | null, responseText: string): unknown {
  if ((contentType ?? "").includes("application/json")) {
    try {
      return JSON.parse(responseText);
    } catch {
      return responseText;
    }
  }
  return responseText;
}

async function executeUpload<T>(
  path: string,
  formData: FormData,
  {
    headers = {},
    skipAuth = false,
    onUploadProgress,
  }: ApiUploadOptions = {},
): Promise<T> {
  const url = toAbsoluteUrl(path);

  const token = !skipAuth ? authBridge?.getAccessToken() : null;

  return await new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url, true);

    Object.entries(headers).forEach(([key, value]) => {
      xhr.setRequestHeader(key, value);
    });
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable || !onUploadProgress) return;
      onUploadProgress(event.loaded, event.total);
    };

    xhr.onerror = () => {
      reject(
        new ApiError(
          `Network error calling ${url}. Check that API gateway is reachable at ${API_BASE_URL}.`,
          0,
          null,
        ),
      );
    };

    xhr.onload = () => {
      const contentType = xhr.getResponseHeader("content-type");
      const detail = parseXhrErrorPayload(contentType, xhr.responseText);
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(detail as T);
        return;
      }
      reject(toApiError(xhr.status, detail));
    };

    xhr.send(formData);
  });
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

export async function apiUpload<T = unknown>(
  path: string,
  formData: FormData,
  options: ApiUploadOptions = {},
): Promise<T> {
  try {
    return await executeUpload<T>(path, formData, options);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401 || options.skipAuth || !authBridge) {
      throw error;
    }
  }

  const nextAccessToken = await authBridge.refreshAccessToken();
  if (!nextAccessToken) {
    throw new ApiError("Authentication required.", 401, null);
  }

  return await executeUpload<T>(path, formData, options);
}
