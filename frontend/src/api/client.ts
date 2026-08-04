// Typed fetch client. Credentials included so the HttpOnly session cookie is sent.
const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:3001";

export interface ApiErrorBody {
  error: { code: string; message: string; details?: Record<string, unknown>; request_id: string };
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { credentials: "include" });
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as ApiErrorBody | null;
    throw new ApiError(res.status, body?.error.code ?? "HTTP_ERROR", body?.error.message ?? res.statusText);
  }
  return (await res.json()) as T;
}
