"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { SITE_NAME } from "@/lib/config";
import { useAuth } from "@/lib/auth";

export function Nav() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  async function onLogout() {
    await logout();
    router.push("/");
  }

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
        <Link href="/" className="font-semibold">
          {SITE_NAME}
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          {loading ? null : user ? (
            <>
              <Link href="/media" className="hover:underline">
                Media
              </Link>
              <Link href="/profile" className="hover:underline">
                Profile
              </Link>
              <button type="button" onClick={onLogout} className="hover:underline">
                Log out
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="hover:underline">
                Log in
              </Link>
              <Link href="/register" className="hover:underline">
                Register
              </Link>
            </>
          )}
        </nav>
      </div>
      {user && !user.is_email_verified ? (
        <div className="border-t border-amber-200 bg-amber-50 px-4 py-2 text-center text-sm text-amber-900">
          Your email address is not verified yet.{" "}
          <Link href="/profile" className="font-medium underline">
            Resend the verification email
          </Link>
        </div>
      ) : null}
    </header>
  );
}
