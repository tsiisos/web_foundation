import { NextRequest, NextResponse } from "next/server";

import { callBackend, setRefreshCookie } from "@/lib/server";

export async function POST(request: NextRequest) {
  let body: Record<string, unknown>;
  try {
    body = (await request.json()) as Record<string, unknown>;
  } catch {
    return NextResponse.json({ detail: "Invalid request." }, { status: 400 });
  }

  const { status, data } = await callBackend("/api/v1/auth/token/", request, {
    email: body.email,
    password: body.password,
  });
  if (status !== 200) return NextResponse.json(data, { status });
  if (typeof data.access !== "string" || typeof data.refresh !== "string") {
    return NextResponse.json({ detail: "Unexpected server response." }, { status: 502 });
  }

  const response = NextResponse.json({ access: data.access });
  setRefreshCookie(response, data.refresh);
  return response;
}
