import { ApiError } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost/api';

export class ApiClientError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiClientError';
  }
}

export async function request<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error: ApiError = await response.json().catch(() => ({
      detail: response.statusText
    }));
    throw new ApiClientError(response.status, error.detail);
  }

  if (response.status === 204) return null as T;
  return response.json();
}
