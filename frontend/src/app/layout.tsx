import type { Metadata } from "next";

import "./globals.css";
import { Nav } from "@/components/Nav";
import { SITE_NAME } from "@/lib/config";
import { AuthProvider } from "@/lib/auth";

export const metadata: Metadata = {
  title: SITE_NAME,
  description: SITE_NAME,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <AuthProvider>
          <Nav />
          <main className="mx-auto max-w-3xl px-4 py-8">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
