import type { MediaAsset } from "./types";

// The access token only lives in memory. The refresh token is an httpOnly cookie handled by /session/*.
let accessToken: string | null = null;
let inflight: Promise<string | null> | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

function labelFor(key: string): string {
  const text = key.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

// Turns Django REST Framework error bodies into a list of readable messages
export function flattenErrors(data: unknown): string[] {
  if (typeof data === "string") {
    return data.trim().startsWith("<") ? [] : [data.slice(0, 300)];
  }
  if (Array.isArray(data)) return data.flatMap(flattenErrors);
  if (data && typeof data === "object") {
    return Object.entries(data as Record<string, unknown>).flatMap(([key, value]) => {
      const messages = flattenErrors(value);
      if (key === "detail" || key === "non_field_errors") return messages;
      return messages.map((message) => `${labelFor(key)}: ${message}`);
    });
  }
  return [];
}

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, data: unknown) {
    super(flattenErrors(data).join(" ") || `Request failed (${status}).`);
    this.status = status;
    this.data = data;
  }
}

export function errorText(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return "Network error. Please try again.";
}

export async function readBody(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

// One refresh at a time, however many requests ask for it
export function refreshSession(): Promise<string | null> {
  if (!inflight) {
    inflight = (async () => {
      try {
        const res = await fetch("/session/refresh", { method: "POST" });
        if (!res.ok) {
          accessToken = null;
          return null;
        }
        const data = (await res.json()) as { access?: string };
        accessToken = data.access ?? null;
        return accessToken;
      } catch {
        return null;
      } finally {
        inflight = null;
      }
    })();
  }
  return inflight;
}

export async function sessionLogin(email: string, password: string): Promise<void> {
  const res = await fetch("/session/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await readBody(res);
  if (!res.ok) throw new ApiError(res.status, data);
  accessToken = (data as { access?: string } | null)?.access ?? null;
}

export async function sessionLogout(): Promise<void> {
  try {
    await fetch("/session/logout", { method: "POST" });
  } catch {
    // the local state is cleared below either way
  }
  accessToken = null;
}

type Options = {
  method?: string;
  json?: unknown;
  auth?: boolean;
};

export async function api<T = unknown>(path: string, options: Options = {}): Promise<T> {
  const { json, auth = true } = options;
  const method = options.method ?? (json === undefined ? "GET" : "POST");

  const send = (token: string | null) => {
    const headers: Record<string, string> = {};
    if (json !== undefined) headers["Content-Type"] = "application/json";
    if (token) headers.Authorization = `Bearer ${token}`;
    return fetch(path, {
      method,
      headers,
      body: json === undefined ? undefined : JSON.stringify(json),
    });
  };

  let token = auth ? (accessToken ?? (await refreshSession())) : null;
  let res = await send(token);
  if (res.status === 401 && auth) {
    token = await refreshSession();
    if (token) res = await send(token);
  }
  const data = await readBody(res);
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}

// XMLHttpRequest, because fetch cannot report upload progress
export async function uploadFile(
  file: File,
  visibility: string,
  onProgress: (percent: number) => void,
): Promise<MediaAsset> {
  const send = (token: string | null) =>
    new Promise<{ status: number; body: unknown }>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "/api/v1/media/");
      if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
      };
      xhr.onload = () => {
        let body: unknown = null;
        try {
          body = JSON.parse(xhr.responseText);
        } catch {
          body = null;
        }
        resolve({ status: xhr.status, body });
      };
      xhr.onerror = () => reject(new Error("network"));
      const form = new FormData();
      form.append("file", file);
      form.append("visibility", visibility);
      xhr.send(form);
    });

  let token = accessToken ?? (await refreshSession());
  let result = await send(token);
  if (result.status === 401) {
    token = await refreshSession();
    result = await send(token);
  }
  if (result.status >= 200 && result.status < 300) return result.body as MediaAsset;
  throw new ApiError(result.status, result.body);
}
