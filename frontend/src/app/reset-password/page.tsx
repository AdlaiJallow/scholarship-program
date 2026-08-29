"use client";

import { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Icon } from "@/components/Icon";
import { Alert } from "@/components/Alert";

function detailOf(err: unknown, fallback: string): string {
  if (!(err instanceof ApiError) || typeof err.detail !== "object" || !err.detail) {
    return fallback;
  }
  const body = err.detail as Record<string, unknown>;
  if (typeof body.detail === "string") {
    return body.detail;
  }
  const fieldErrors = Object.values(body)
    .flat()
    .filter((value): value is string => typeof value === "string");
  return fieldErrors.length > 0 ? fieldErrors.join(" ") : fallback;
}

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const uid = searchParams.get("uid") ?? "";
  const token = searchParams.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const passwordMismatch = passwordConfirm.length > 0 && password !== passwordConfirm;
  const linkMissing = !uid || !token;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (password !== passwordConfirm) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await api.post("/auth/password-reset/confirm", { uid, token, new_password: password });
      setDone(true);
      setTimeout(() => router.push("/login"), 2500);
    } catch (err) {
      setError(detailOf(err, "We could not reset your password. Please try again."));
    } finally {
      setSubmitting(false);
    }
  }

  if (linkMissing) {
    return (
      <Alert tone="error" title="Invalid reset link">
        This password reset link is missing or malformed. Please request a new one.
      </Alert>
    );
  }

  if (done) {
    return (
      <Alert tone="success" title="Password updated">
        Your password has been reset. Redirecting you to sign in…
      </Alert>
    );
  }

  return (
    <>
      {error && <Alert tone="error">{error}</Alert>}
      <form className="panel" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="password">New password</label>
          <input
            id="password"
            type="password"
            required
            minLength={12}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            autoFocus
          />
          <span className="hint">At least 12 characters, with an uppercase letter, a lowercase letter, and a number or symbol.</span>
        </div>
        <div className={`field${passwordMismatch ? " has-error" : ""}`} style={{ marginBottom: "var(--space-5)" }}>
          <label htmlFor="password_confirm">Confirm new password</label>
          <input
            id="password_confirm"
            type="password"
            required
            value={passwordConfirm}
            onChange={(e) => setPasswordConfirm(e.target.value)}
            autoComplete="new-password"
          />
          {passwordMismatch && <span className="field-error">Passwords do not match.</span>}
        </div>
        <button type="submit" className="btn btn-primary btn-block" disabled={submitting || passwordMismatch}>
          {submitting && <span className="spinner" />}
          {submitting ? "Resetting…" : "Reset password"}
        </button>
      </form>
    </>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="shell-narrow" style={{ maxWidth: 400, margin: "var(--space-8) auto 0" }}>
      <Link href="/login" className="back-link">
        <Icon name="chevron-left" size={15} />
        Back to sign in
      </Link>
      <div style={{ textAlign: "center", marginBottom: "var(--space-6)" }}>
        <h1>Reset password</h1>
        <p className="muted" style={{ marginBottom: 0 }}>Choose a new password for your account.</p>
      </div>
      <Suspense fallback={null}>
        <ResetPasswordForm />
      </Suspense>
    </div>
  );
}
