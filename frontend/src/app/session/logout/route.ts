import { NextResponse } from "next/server";

import { clearRefreshCookie } from "@/lib/server";

export async function POST() {
  const response = NextResponse.json({ detail: "Logged out." });
  clearRefreshCookie(response);
  return response;
}
