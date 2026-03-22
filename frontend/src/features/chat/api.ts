import { authorizedFetch } from "./auth";

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await authorizedFetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      detail = payload?.detail?.message || payload?.detail || detail;
    } catch {
      // ignore parse error
    }
    throw new Error(detail);
  }

  if (response.status === 204) return {} as T;
  return response.json() as Promise<T>;
}

export async function requestForm<T>(
  path: string,
  formData: FormData,
  init?: Omit<RequestInit, "body">,
): Promise<T> {
  const response = await authorizedFetch(path, {
    ...init,
    method: init?.method ?? "POST",
    body: formData,
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      detail = payload?.detail?.message || payload?.detail || detail;
    } catch {
      // ignore parse error
    }
    throw new Error(detail);
  }

  if (response.status === 204) return {} as T;
  return response.json() as Promise<T>;
}
