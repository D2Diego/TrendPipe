const API_BASE = "/api/v1";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

interface Envelope<T> { status: number; data?: T; message?: string }

async function handle<T>(response: Response): Promise<T> {
  let body: Envelope<T>;
  try {
    body = await response.json() as Envelope<T>;
  } catch {
    throw new ApiError(response.status, `request failed with ${response.status}`);
  }
  if (!response.ok) throw new ApiError(response.status, body.message || `request failed with ${response.status}`);
  return body.data as T;
}

export async function apiGet<T>(path: string, params?: Record<string, string>): Promise<T> {
  const query = params ? `?${new URLSearchParams(params)}` : "";
  return handle<T>(await fetch(`${API_BASE}${path}${query}`));
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return handle<T>(await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  }));
}

export async function apiPut<T>(path: string, body?: unknown): Promise<T> {
  return handle<T>(await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  }));
}

export async function apiDelete<T>(path: string): Promise<T> {
  return handle<T>(await fetch(`${API_BASE}${path}`, { method: "DELETE" }));
}

export async function apiUpload<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  return handle<T>(await fetch(`${API_BASE}${path}`, { method: "POST", body: form }));
}
