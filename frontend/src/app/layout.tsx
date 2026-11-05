import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "web_foundation",
  description: "web_foundation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
