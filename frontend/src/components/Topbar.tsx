"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export function Topbar() {
  const router = useRouter();

  async function handleLogout() {
    try {
      await api.post("/auth/logout");
    } finally {
      router.push("/login");
    }
  }

  return (
    <header className="topbar">
      <Link href="/" className="brand" style={{ color: "#f3f2ea", textDecoration: "none" }}>
        Scholarship Verification Portal
      </Link>
      <nav>
        <Link href="/dashboard">My Application</Link>
        <Link href="/admin/queue">Ministry Queue</Link>
        <button type="button" className="link" onClick={handleLogout}>
          Sign out
        </button>
      </nav>
    </header>
  );
}
