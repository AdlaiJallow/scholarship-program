import type { Metadata } from "next";
import "./globals.css";
import { Topbar } from "@/components/Topbar";

export const metadata: Metadata = {
  title: "Scholarship Verification Portal",
  description: "Self-verification and approval portal for Ministry scholarship holders.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Topbar />
        <main className="shell">{children}</main>
      </body>
    </html>
  );
}
