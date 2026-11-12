"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Card, buttonClass, secondaryButtonClass } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { SITE_NAME } from "@/lib/config";

export default function Home() {
  const { user, loading } = useAuth();
  const [status, setStatus] = useState("checking...");

  useEffect(() => {
    fetch("/api/v1/health/")
      .then((res) => res.json())
      .then((data) => setStatus(data.status))
      .catch(() => setStatus("unreachable"));
  }, []);

  return (
    <Card title={SITE_NAME}>
      <p>
        Backend status: <span className="font-mono">{status}</span>
      </p>
      {loading ? null : user ? (
        <div className="flex gap-3">
          <Link href="/media" className={buttonClass}>
            My media
          </Link>
          <Link href="/profile" className={secondaryButtonClass}>
            Profile
          </Link>
        </div>
      ) : (
        <div className="flex gap-3">
          <Link href="/login" className={buttonClass}>
            Log in
          </Link>
          <Link href="/register" className={secondaryButtonClass}>
            Create an account
          </Link>
        </div>
      )}
    </Card>
  );
}
