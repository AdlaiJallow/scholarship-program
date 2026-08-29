"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Icon } from "@/components/Icon";
import { Alert } from "@/components/Alert";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      // Login itself needs no CSRF token (DRF only enforces CSRF once a
      // session is already authenticated) and its response sets a fresh
      // csrftoken cookie that every request after this one will use.
      const result = await api.post<{ user_type: "student" | "officer" }>("/auth/login", { email, password });
      router.push(result.user_type === "student" ? "/dashboard" : "/admin/queue");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(typeof err.detail === "object" && err.detail && "detail" in (err.detail as any)
          ? (err.detail as any).detail
          : "Incorrect email or password.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="shell-narrow" style={{ maxWidth: 400, margin: "var(--space-8) auto 0" }}>
      <Link href="/" className="back-link">
        <Icon name="chevron-left" size={15} />
        Back
      </Link>
      <div style={{ textAlign: "center", marginBottom: "var(--space-6)" }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/images/moherst-logo.jpeg"
          alt="Ministry of Higher Education, Research, Science and Technology"
          width={64}
          height={64}
          style={{ display: "block", margin: "0 auto var(--space-3)", borderRadius: "12px" }}
        />
        <h1>Sign in</h1>
        <p className="muted" style={{ marginBottom: 0 }}>Access your scholarship verification account.</p>
      </div>

      {error && <Alert tone="error">{error}</Alert>}

      <form className="panel" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="email">Email address</label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
        </div>
        <div className="field" style={{ marginBottom: "var(--space-5)" }}>
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </div>
        <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
          {submitting && <span className="spinner" />}
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="muted" style={{ textAlign: "center", marginTop: "var(--space-4)" }}>
        First time here? <a href="/activate">Activate your scholarship account</a>
      </p>
    </div>
  );
}
