import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "INSURELAKE - Executive Control Centre",
  description:
    "Real-time governed insurance lakehouse for actuarial analytics, fraud intelligence and executive decision-making.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-ink font-sans antialiased">{children}</body>
    </html>
  );
}
