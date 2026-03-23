function isLoopbackHost(hostname: string): boolean {
  const host = hostname.trim().toLowerCase();
  return host === "localhost" || host === "127.0.0.1" || host === "::1";
}

function resolveApiBaseUrl(): string {
  const envValue = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "");
  if (typeof window === "undefined") {
    return envValue ?? "http://localhost/api";
  }

  const runtimeDefault = `${window.location.protocol}//${window.location.hostname}/api`;
  if (!envValue) return runtimeDefault;

  try {
    const parsed = new URL(envValue);
    // If env is loopback but page is opened via LAN/domain host, prefer current page host.
    if (isLoopbackHost(parsed.hostname) && !isLoopbackHost(window.location.hostname)) {
      return runtimeDefault;
    }
    return envValue;
  } catch {
    return envValue;
  }
}

export const API_BASE_URL = resolveApiBaseUrl();

export const WS_BASE_URL =
  process.env.NEXT_PUBLIC_WS_URL?.replace(/\/+$/, "") ?? "ws://localhost";
