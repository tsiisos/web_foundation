"use client";

import Link from "next/link";
import { useState } from "react";

import { Alert, Card, Field, buttonClass, inputClass, linkClass } from "@/components/ui";
import { api, errorText } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api("/api/v1/auth/password-reset/", { json: { email }, auth: false });
      setSent(true);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title="Forgot your password?">
      {sent ? (
        <Alert kind="success">If an account with that email exists, a reset link is on its way.</Alert>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4">
          {error ? <Alert kind="error">{error}</Alert> : null}
          <Field label="Email">
            <input type="email" required autoComplete="email" className={inputClass} value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <button type="submit" className={buttonClass} disabled={busy}>
            {busy ? "Sending…" : "Send reset link"}
          </button>
        </form>
      )}
      <Link href="/login" className={linkClass}>
        Back to log in
      </Link>
    </Card>
  );
}
