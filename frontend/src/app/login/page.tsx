"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

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
    <div className="stack" style={{ maxWidth: 420 }}>
      <h1>Sign in</h1>
      {error && <div className="error-banner">{error}</div>}
      <form className="card" onSubmit={handleSubmit}>
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
        <div className="field">
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
        <button type="submit" className="btn btn-primary" disabled={submitting} style={{ width: "100%" }}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="muted">
        First time here? <a href="/activate">Activate your scholarship account</a> using the code the Ministry
        gave you.
      </p>
    </div>
  );
}
