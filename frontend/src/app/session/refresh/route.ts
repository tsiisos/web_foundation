import { NextRequest, NextResponse } from "next/server";

import { REFRESH_COOKIE, callBackend, clearRefreshCookie } from "@/lib/server";

export async function POST(request: NextRequest) {
  const refresh = request.cookies.get(REFRESH_COOKIE)?.value;
  if (!refresh) return NextResponse.json({ detail: "No session." }, { status: 401 });

  const { status, data } = await callBackend("/api/v1/auth/token/refresh/", request, { refresh });
  if (status === 400 || status === 401) {
    const response = NextResponse.json({ detail: "Session expired." }, { status: 401 });
    clearRefreshCookie(response);
    return response;
  }
  if (status !== 200 || typeof data.access !== "string") {
    return NextResponse.json({ detail: "The server is unavailable. Please try again." }, { status: 502 });
  }
  return NextResponse.json({ access: data.access });
}
