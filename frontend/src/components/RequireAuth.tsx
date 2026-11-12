"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/lib/auth";
import type { User } from "@/lib/types";

export function RequireAuth({ children }: { children: (user: User) => React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) return <p className="text-sm text-slate-500">Loading…</p>;
  return <>{children(user)}</>;
}
