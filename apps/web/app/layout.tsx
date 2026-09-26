import type { Metadata } from "next";
import "./globals.css";
import { ResearchShell } from "@/components/ResearchShell";

export const metadata: Metadata = {
  title: "PRJ_277 | Regional Media Research",
  description: "An evidence-linked 360-degree view of Government of India news coverage across regional media.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <ResearchShell>{children}</ResearchShell>
      </body>
    </html>
  );
}
