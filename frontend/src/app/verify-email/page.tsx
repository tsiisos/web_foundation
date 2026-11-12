"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { Alert, Card, linkClass } from "@/components/ui";
import { api, errorText } from "@/lib/api";
import { useAuth } from "@/lib/auth";

function VerifyEmail() {
  const params = useSearchParams();
  const uid = params.get("uid");
  const token = params.get("token");
  const { reloadUser } = useAuth();
  const complete = Boolean(uid && token);
  const [state, setState] = useState<"working" | "ok" | "error">(complete ? "working" : "error");
  const [message, setMessage] = useState(complete ? "" : "This link is incomplete.");
  const started = useRef(false);

  useEffect(() => {
    // The link works only once, so make sure the request is sent only once (also in dev mode)
    if (!uid || !token || started.current) return;
    started.current = true;
    (async () => {
      try {
        await api("/api/v1/auth/verify-email/", { json: { uid, token }, auth: false });
        setState("ok");
        await reloadUser();
      } catch (err) {
        setState("error");
        setMessage(errorText(err));
      }
    })();
  }, [uid, token, reloadUser]);

  return (
    <Card title="Email verification">
      {state === "working" ? <p className="text-sm text-slate-500">Verifying…</p> : null}
      {state === "ok" ? <Alert kind="success">Your email address is verified.</Alert> : null}
      {state === "error" ? <Alert kind="error">{message}</Alert> : null}
      <Link href="/login" className={linkClass}>
        Continue
      </Link>
    </Card>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Loading…</p>}>
      <VerifyEmail />
    </Suspense>
  );
}
