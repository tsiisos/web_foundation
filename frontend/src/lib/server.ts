// Server-side helpers for the /session/* route handlers
import type { NextRequest, NextResponse } from "next/server";

export const REFRESH_COOKIE = "refresh_token";
// Keep in sync with SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"] in the Django settings
const REFRESH_MAX_AGE = 60 * 60 * 24 * 7;
const BACKEND_URL = process.env.API_INTERNAL_URL ?? "http://backend:8000";

type BackendResult = { status: number; data: Record<string, unknown> };

export async function callBackend(path: string, request: NextRequest, body: unknown): Promise<BackendResult> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  // Without this, Django's rate limit would see every user as the same address
  const forwarded = request.headers.get("x-forwarded-for");
  if (forwarded) headers["X-Forwarded-For"] = forwarded;
  try {
    const res = await fetch(`${BACKEND_URL}${path}`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const data = (await res.json().catch(() => ({}))) as Record<string, unknown>;
    return { status: res.status, data };
  } catch {
    return { status: 502, data: { detail: "The server is unavailable. Please try again." } };
  }
}

function cookieOptions() {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    // Set COOKIE_SECURE=true on the frontend container once the site is served over HTTPS
    secure: process.env.COOKIE_SECURE === "true",
    path: "/session",
  };
}

export function setRefreshCookie(response: NextResponse, token: string) {
  response.cookies.set(REFRESH_COOKIE, token, { ...cookieOptions(), maxAge: REFRESH_MAX_AGE });
}

export function clearRefreshCookie(response: NextResponse) {
  response.cookies.set(REFRESH_COOKIE, "", { ...cookieOptions(), maxAge: 0 });
}
