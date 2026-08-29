"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Icon } from "@/components/Icon";
import { Alert } from "@/components/Alert";
import { PasswordResetRequestResponse } from "@/lib/types";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    try {
      // The API always responds 202 whether or not the email is registered,
      // so there is nothing to branch on here — just show the same message.
      await api.post<PasswordResetRequestResponse>("/auth/password-reset", { email });
    } finally {
      setSubmitting(false);
      setSubmitted(true);
    }
  }

  return (
    <div className="shell-narrow" style={{ maxWidth: 400, margin: "var(--space-8) auto 0" }}>
      <Link href="/login" className="back-link">
        <Icon name="chevron-left" size={15} />
        Back to sign in
      </Link>
      <div style={{ textAlign: "center", marginBottom: "var(--space-6)" }}>
        <h1>Forgot password</h1>
        <p className="muted" style={{ marginBottom: 0 }}>
          Enter the email address on your account and we&apos;ll send you a link to reset your password.
        </p>
      </div>

      {submitted ? (
        <Alert tone="success" title="Check your email">
          If an account exists for {email}, we&apos;ve sent a password reset link to it. The link expires soon, so
          use it right away.
        </Alert>
      ) : (
        <form className="panel" onSubmit={handleSubmit}>
          <div className="field" style={{ marginBottom: "var(--space-5)" }}>
            <label htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              autoFocus
            />
          </div>
          <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
            {submitting && <span className="spinner" />}
            {submitting ? "Sending…" : "Send reset link"}
          </button>
        </form>
      )}
    </div>
  );
}
