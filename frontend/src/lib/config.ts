export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "") ?? "http://localhost/api";

export const WS_BASE_URL =
  process.env.NEXT_PUBLIC_WS_URL?.replace(/\/+$/, "") ?? "ws://localhost";

