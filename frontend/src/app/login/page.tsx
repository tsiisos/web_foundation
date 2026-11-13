"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Alert, Card, Field, buttonClass, inputClass, linkClass } from "@/components/ui";
import { errorText } from "@/lib/api";
import { useAuth } from "@/lib/auth";

function PasswordChangedNotice() {
  const params = useSearchParams();
  if (params.get("notice") !== "password-changed") return null;
  return <Alert kind="success">Your password was changed. Please log in again.</Alert>;
}

export default function LoginPage() {
  const { user, loading, login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace("/profile");
  }, [loading, user, router]);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Log in">
      <Suspense fallback={null}>
        <PasswordChangedNotice />
      </Suspense>
      <form onSubmit={onSubmit} className="space-y-4">
        {error ? <Alert kind="error">{error}</Alert> : null}
        <Field label="Email">
          <input type="email" required autoComplete="email" className={inputClass} value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Password">
          <input type="password" required autoComplete="current-password" className={inputClass} value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <button type="submit" className={buttonClass} disabled={busy}>
          {busy ? "Logging in…" : "Log in"}
        </button>
      </form>
      <p className="text-sm text-slate-600">
        <Link href="/forgot-password" className={linkClass}>
          Forgot your password?
        </Link>{" "}
        ·{" "}
        <Link href="/register" className={linkClass}>
          Create an account
        </Link>
      </p>
    </Card>
  );
}
