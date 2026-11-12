"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { Alert, Card, Field, buttonClass, inputClass, linkClass } from "@/components/ui";
import { api, errorText } from "@/lib/api";

function ResetPassword() {
  const params = useSearchParams();
  const uid = params.get("uid");
  const token = params.get("token");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError("The passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await api("/api/v1/auth/password-reset/confirm/", {
        json: { uid, token, new_password: password },
        auth: false,
      });
      setDone(true);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  if (!uid || !token) {
    return (
      <Card title="Choose a new password">
        <Alert kind="error">This link is incomplete.</Alert>
        <Link href="/forgot-password" className={linkClass}>
          Request a new link
        </Link>
      </Card>
    );
  }

  return (
    <Card title="Choose a new password">
      {done ? (
        <>
          <Alert kind="success">Your password was updated.</Alert>
          <Link href="/login" className={linkClass}>
            Log in
          </Link>
        </>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4">
          {error ? <Alert kind="error">{error}</Alert> : null}
          <Field label="New password" hint="At least 8 characters. Not a common password, and not only digits.">
            <input type="password" required autoComplete="new-password" className={inputClass} value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <Field label="Repeat the new password">
            <input type="password" required autoComplete="new-password" className={inputClass} value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          </Field>
          <button type="submit" className={buttonClass} disabled={busy}>
            {busy ? "Saving…" : "Save password"}
          </button>
        </form>
      )}
    </Card>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Loading…</p>}>
      <ResetPassword />
    </Suspense>
  );
}
