"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Icon } from "@/components/Icon";

const LINKS = [
  { href: "/dashboard", label: "My Application", roles: ["student"] },
  { href: "/admin/queue", label: "Ministry Queue", roles: ["officer"] },
];

export function Topbar() {
  const router = useRouter();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [userType, setUserType] = useState<"student" | "officer" | null>(null);

  useEffect(() => {
    api
      .get<{ user_type: "student" | "officer" }>("/me/profile")
      .then((profile) => setUserType(profile.user_type))
      .catch(() => setUserType(null));
  }, [pathname]);

  const links = LINKS.filter((link) => userType && link.roles.includes(userType));

  async function handleLogout() {
    try {
      await api.post("/auth/logout");
    } finally {
      router.push("/login");
    }
  }

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <Link href="/" className="brand">
          <span className="brand-mark brand-mark-logo">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/images/moherst-logo.jpeg" alt="Ministry of Higher Education, Research, Science and Technology" />
          </span>
          Scholarship Verification Portal
        </Link>
        <nav className="desktop-nav">
          {links.map((link) => (
            <Link key={link.href} href={link.href} data-active={pathname?.startsWith(link.href)}>
              {link.label}
            </Link>
          ))}
          {userType && (
            <button type="button" className="link" onClick={handleLogout}>
              <Icon name="log-out" size={15} />
              Sign out
            </button>
          )}
        </nav>
        <button
          type="button"
          className="menu-toggle"
          onClick={() => setMenuOpen((v) => !v)}
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          aria-expanded={menuOpen}
        >
          <Icon name={menuOpen ? "x" : "menu"} size={20} />
        </button>
      </div>
      <nav className="mobile-nav" data-open={menuOpen}>
        {links.map((link) => (
          <Link key={link.href} href={link.href} onClick={() => setMenuOpen(false)}>
            {link.label}
          </Link>
        ))}
        {userType && (
          <button type="button" className="link" onClick={handleLogout}>
            Sign out
          </button>
        )}
      </nav>
    </header>
  );
}
