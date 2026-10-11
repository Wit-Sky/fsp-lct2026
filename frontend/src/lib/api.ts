// Типизированный клиент API. Типы — из OpenAPI бэкенда: `npm run gen:api` перегенерирует api-schema.ts.
import type { components } from "./api-schema";
import { recordQaEvent } from "./qa";

export type S = components["schemas"];
export type Token = S["TokenOut"];
export type Role = "candidate" | "employer";

const TOKEN_KEY = "fsp_token";

export const tokenStore = {
  get(): Token | null {
    try {
      const raw = localStorage.getItem(TOKEN_KEY);
      return raw ? (JSON.parse(raw) as Token) : null;
    } catch {
      return null;
    }
  },
  set(t: Token | null) {
    try {
      if (t) localStorage.setItem(TOKEN_KEY, JSON.stringify(t));
      else localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* приватный режим — живём без сохранения */
    }
  },
};

/** Ошибка API в формате бэкенда `{detail, code}`. */
export class ApiError extends Error {
  constructor(public status: number, message: string, public code?: string) {
    super(message);
  }
}

type Method = "GET" | "POST" | "PUT" | "DELETE";

export async function api<T>(method: Method, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token.access_token}`;
  let payload: BodyInit | undefined;
  if (body instanceof FormData) payload = body;
  else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(`/api${path}`, { method, headers, body: payload });
  if (res.status === 401 && token) {
    tokenStore.set(null);
    window.dispatchEvent(new Event("fsp:logout"));
  }
  if (!res.ok) {
    let detail = res.statusText;
    let code: string | undefined;
    try {
      const err = await res.json();
      code = err.code;
      detail = typeof err.detail === "string" ? err.detail : (err.detail?.[0]?.msg ?? detail);
    } catch {
      /* не JSON */
    }
    recordQaEvent("api", `${method} /api${path} → ${res.status}${code ? ` ${code}` : ""}: ${detail}`);
    throw new ApiError(res.status, detail, code);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const get = <T>(path: string) => api<T>("GET", path);
export const post = <T>(path: string, body?: unknown) => api<T>("POST", path, body);
export const put = <T>(path: string, body?: unknown) => api<T>("PUT", path, body);
