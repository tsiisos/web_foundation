"use client";

import { useState } from "react";

import { RequireAuth } from "@/components/RequireAuth";
import { Alert, Card, Field, buttonClass, inputClass, secondaryButtonClass } from "@/components/ui";
import { api, errorText, sessionLogout } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { User } from "@/lib/types";

type Notice = { kind: "success" | "error"; text: string } | null;

function PasswordCard() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    if (next !== confirm) {
      setError("The new passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await api("/api/v1/users/me/password/", { json: { current_password: current, new_password: next } });
      await sessionLogout();
      // A full page load resets all state, and the login page can show a notice
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.assign("/login?notice=password-changed");
    } catch (err) {
      setError(errorText(err));
      setBusy(false);
    }
  }

  return (
    <Card title="Change password">
      <form onSubmit={onSubmit} className="space-y-4">
        {error ? <Alert kind="error">{error}</Alert> : null}
        <Field label="Current password">
          <input type="password" required autoComplete="current-password" className={inputClass} value={current} onChange={(e) => setCurrent(e.target.value)} />
        </Field>
        <Field label="New password" hint="At least 8 characters. Not a common password, and not only digits. You will be logged out everywhere.">
          <input type="password" required autoComplete="new-password" className={inputClass} value={next} onChange={(e) => setNext(e.target.value)} />
        </Field>
        <Field label="Repeat the new password">
          <input type="password" required autoComplete="new-password" className={inputClass} value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        </Field>
        <button type="submit" className={buttonClass} disabled={busy}>
          {busy ? "Saving…" : "Change password"}
        </button>
      </form>
    </Card>
  );
}

function DeleteCard() {
  const [password, setPassword] = useState("");
  const [sure, setSure] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api("/api/v1/users/me/delete/", { json: { password } });
      await sessionLogout();
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.assign("/");
    } catch (err) {
      setError(errorText(err));
      setBusy(false);
    }
  }

  return (
    <Card title="Delete account">
      <form onSubmit={onSubmit} className="space-y-4">
        <p className="text-sm text-slate-600">This permanently deletes your account and all files you uploaded. It cannot be undone.</p>
        {error ? <Alert kind="error">{error}</Alert> : null}
        <Field label="Your password">
          <input type="password" required autoComplete="current-password" className={inputClass} value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={sure} onChange={(e) => setSure(e.target.checked)} />
          I understand that this cannot be undone
        </label>
        <button type="submit" className={buttonClass} disabled={busy || !sure || !password}>
          {busy ? "Deleting…" : "Delete my account"}
        </button>
      </form>
    </Card>
  );
}

function Profile({ user }: { user: User }) {
  const { setUser } = useAuth();
  const [firstName, setFirstName] = useState(user.first_name);
  const [lastName, setLastName] = useState(user.last_name);
  const [isCustomer, setIsCustomer] = useState(user.is_customer);
  const [isProvider, setIsProvider] = useState(user.is_provider);
  const [nameNotice, setNameNotice] = useState<Notice>(null);
  const [rolesNotice, setRolesNotice] = useState<Notice>(null);
  const [verifyNotice, setVerifyNotice] = useState<Notice>(null);

  async function saveName(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setNameNotice(null);
    try {
      const updated = await api<User>("/api/v1/users/me/", {
        method: "PATCH",
        json: { first_name: firstName, last_name: lastName },
      });
      setUser(updated);
      setNameNotice({ kind: "success", text: "Saved." });
    } catch (err) {
      setNameNotice({ kind: "error", text: errorText(err) });
    }
  }

  async function saveRoles(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setRolesNotice(null);
    if (!isCustomer && !isProvider) {
      setRolesNotice({ kind: "error", text: "Keep at least one role." });
      return;
    }
    try {
      const roles = await api<{ is_customer: boolean; is_provider: boolean }>("/api/v1/users/me/roles/", {
        method: "PATCH",
        json: { is_customer: isCustomer, is_provider: isProvider },
      });
      setUser({ ...user, ...roles });
      setRolesNotice({ kind: "success", text: "Saved." });
    } catch (err) {
      setRolesNotice({ kind: "error", text: errorText(err) });
    }
  }

  async function resend() {
    setVerifyNotice(null);
    try {
      await api("/api/v1/auth/resend-verification/", { method: "POST" });
      setVerifyNotice({ kind: "success", text: "Verification email sent." });
    } catch (err) {
      setVerifyNotice({ kind: "error", text: errorText(err) });
    }
  }

  return (
    <div className="space-y-6">
      <Card title="Account">
        <p className="text-sm">
          Signed in as <span className="font-medium">{user.email}</span>
        </p>
        {user.is_email_verified ? (
          <Alert kind="success">Your email address is verified.</Alert>
        ) : (
          <div className="space-y-2">
            <Alert kind="info">Your email address is not verified yet. You need it to upload files.</Alert>
            {verifyNotice ? <Alert kind={verifyNotice.kind}>{verifyNotice.text}</Alert> : null}
            <button type="button" className={secondaryButtonClass} onClick={resend}>
              Resend verification email
            </button>
          </div>
        )}
      </Card>

      <Card title="Name">
        <form onSubmit={saveName} className="space-y-4">
          {nameNotice ? <Alert kind={nameNotice.kind}>{nameNotice.text}</Alert> : null}
          <div className="grid grid-cols-2 gap-4">
            <Field label="First name">
              <input className={inputClass} value={firstName} onChange={(e) => setFirstName(e.target.value)} />
            </Field>
            <Field label="Last name">
              <input className={inputClass} value={lastName} onChange={(e) => setLastName(e.target.value)} />
            </Field>
          </div>
          <button type="submit" className={buttonClass}>
            Save name
          </button>
        </form>
      </Card>

      <Card title="Roles">
        <form onSubmit={saveRoles} className="space-y-4">
          {rolesNotice ? <Alert kind={rolesNotice.kind}>{rolesNotice.text}</Alert> : null}
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={isCustomer} onChange={(e) => setIsCustomer(e.target.checked)} />
            Customer
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={isProvider} onChange={(e) => setIsProvider(e.target.checked)} />
            Provider
          </label>
          <button type="submit" className={buttonClass}>
            Save roles
          </button>
        </form>
      </Card>

      <PasswordCard />
      <DeleteCard />
    </div>
  );
}

export default function ProfilePage() {
  return <RequireAuth>{(user) => <Profile user={user} />}</RequireAuth>;
}
