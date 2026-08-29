import type { Metadata } from "next";
import { Public_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { Topbar } from "@/components/Topbar";

const publicSans = Public_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Scholarship Verification Portal",
  description: "Self-verification and approval portal for Ministry scholarship holders.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${publicSans.variable} ${plexMono.variable}`}>
      <body>
        <Topbar />
        <main className="shell">{children}</main>
      </body>
    </html>
  );
}
