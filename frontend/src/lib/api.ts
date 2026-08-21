const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : "Request failed");
    this.status = status;
    this.detail = detail;
  }
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * Every mutating request needs the Django CSRF cookie echoed back as a
 * header (system specification §16 — CSRF protection on all state-changing
 * requests). The cookie is only set once the browser has hit the API at
 * least once, so callers should GET something (e.g. /me/profile) before
 * the first POST in a fresh session.
 */
function csrfHeader(): Record<string, string> {
  const token = readCookie("csrftoken");
  return token ? { "X-CSRFToken": token } : {};
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  isMultipart?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, isMultipart = false } = options;

  const headers: Record<string, string> = { Accept: "application/json" };
  let requestBody: BodyInit | undefined;

  if (body !== undefined) {
    if (isMultipart) {
      requestBody = body as FormData;
    } else {
      headers["Content-Type"] = "application/json";
      requestBody = JSON.stringify(body);
    }
  }

  if (method !== "GET") {
    Object.assign(headers, csrfHeader());
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: requestBody,
    credentials: "include",
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) {
    throw new ApiError(response.status, data);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body }),
  postForm: <T>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form, isMultipart: true }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

export function exportDownloadUrl(params: Record<string, string>) {
  const search = new URLSearchParams(params).toString();
  return `${API_BASE_URL}/admin/export?${search}`;
}
