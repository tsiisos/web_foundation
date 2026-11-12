"use client";

import Link from "next/link";
import { useState } from "react";

import { Alert, Card, Field, buttonClass, inputClass, linkClass } from "@/components/ui";
import { api, errorText } from "@/lib/api";

export default function RegisterPage() {
  const [form, setForm] = useState({ first_name: "", last_name: "", email: "", password: "" });
  // Rename these roles per project (see users/models.py)
  const [isCustomer, setIsCustomer] = useState(true);
  const [isProvider, setIsProvider] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const update = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: e.target.value });

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    if (!isCustomer && !isProvider) {
      setError("Choose at least one role.");
      return;
    }
    setBusy(true);
    try {
      await api("/api/v1/auth/register/", {
        json: { ...form, is_customer: isCustomer, is_provider: isProvider },
        auth: false,
      });
      setDone(true);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <Card title="Check your email">
        <Alert kind="success">We sent a verification link to {form.email}. Open it to confirm your address.</Alert>
        <Link href="/login" className={linkClass}>
          Go to log in
        </Link>
      </Card>
    );
  }

  return (
    <Card title="Create an account">
      <form onSubmit={onSubmit} className="space-y-4">
        {error ? <Alert kind="error">{error}</Alert> : null}
        <div className="grid grid-cols-2 gap-4">
          <Field label="First name">
            <input className={inputClass} autoComplete="given-name" value={form.first_name} onChange={update("first_name")} />
          </Field>
          <Field label="Last name">
            <input className={inputClass} autoComplete="family-name" value={form.last_name} onChange={update("last_name")} />
          </Field>
        </div>
        <Field label="Email">
          <input type="email" required autoComplete="email" className={inputClass} value={form.email} onChange={update("email")} />
        </Field>
        <Field label="Password" hint="At least 8 characters. Not a common password, and not only digits.">
          <input type="password" required autoComplete="new-password" className={inputClass} value={form.password} onChange={update("password")} />
        </Field>
        <fieldset className="space-y-2 text-sm">
          <legend className="font-medium text-slate-700">I want to</legend>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={isCustomer} onChange={(e) => setIsCustomer(e.target.checked)} />
            Use the service (customer)
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={isProvider} onChange={(e) => setIsProvider(e.target.checked)} />
            Offer services or listings (provider)
          </label>
        </fieldset>
        <button type="submit" className={buttonClass} disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </button>
      </form>
      <p className="text-sm text-slate-600">
        Already registered?{" "}
        <Link href="/login" className={linkClass}>
          Log in
        </Link>
      </p>
    </Card>
  );
}
