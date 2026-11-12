"use client";

import { useState } from "react";

import { RequireAuth } from "@/components/RequireAuth";
import { Alert, Card, Field, buttonClass, inputClass, secondaryButtonClass } from "@/components/ui";
import { api, errorText } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { User } from "@/lib/types";

type Notice = { kind: "success" | "error"; text: string } | null;

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
    </div>
  );
}

export default function ProfilePage() {
  return <RequireAuth>{(user) => <Profile user={user} />}</RequireAuth>;
}
