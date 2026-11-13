import { NextRequest, NextResponse } from "next/server";

import { REFRESH_COOKIE, callBackend, clearRefreshCookie } from "@/lib/server";

export async function POST(request: NextRequest) {
  const refresh = request.cookies.get(REFRESH_COOKIE)?.value;
  if (refresh) {
    // Best effort: the cookie is cleared below even if the server cannot be reached
    await callBackend("/api/v1/auth/token/blacklist/", request, { refresh });
  }
  const response = NextResponse.json({ detail: "Logged out." });
  clearRefreshCookie(response);
  return response;
}
