"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { Alert } from "@/components/Alert";
import { Icon } from "@/components/Icon";
import {
  CreateAccountResponse,
  ResendCodeResponse,
  VerifyCodeResponse,
  VerifyIdentityResponse,
} from "@/lib/types";

const UTG_EMAIL_SUFFIX = "@utg.edu.gm";
const RESEND_COOLDOWN_SECONDS = 60;

type Step = "identity" | "code" | "account" | "already_activated";

const STEP_NUMBER: Record<Step, number> = { identity: 1, code: 2, account: 3, already_activated: 3 };

function detailOf(err: unknown, fallback: string): string {
  if (!(err instanceof ApiError) || typeof err.detail !== "object" || !err.detail) {
    return fallback;
  }
  const body = err.detail as Record<string, unknown>;
  if (typeof body.detail === "string") {
    return body.detail;
  }
  // Serializer validation errors (e.g. a weak password) come back as
  // { field: ["message", ...] } rather than { detail: "..." } — surface
  // them instead of silently falling back to a generic message.
  const fieldErrors = Object.values(body)
    .flat()
    .filter((value): value is string => typeof value === "string");
  if (fieldErrors.length > 0) {
    return fieldErrors.join(" ");
  }
  return fallback;
}

function isAlreadyActivated(err: unknown): boolean {
  return err instanceof ApiError && typeof err.detail === "object" && err.detail !== null && (err.detail as any).already_activated === true;
}

export default function ActivatePage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("identity");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [matNumber, setMatNumber] = useState("");
  const [utgEmail, setUtgEmail] = useState("");
  const [code, setCode] = useState("");
  const [verificationToken, setVerificationToken] = useState("");

  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [address, setAddress] = useState("");
  const [gender, setGender] = useState("");

  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => setCooldown((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  const matNumberInvalid = matNumber.length > 0 && !/^\d{8}$/.test(matNumber);
  const utgEmailInvalid = utgEmail.length > 0 && !utgEmail.toLowerCase().endsWith(UTG_EMAIL_SUFFIX);
  const passwordMismatch = passwordConfirm.length > 0 && password !== passwordConfirm;

  async function handleVerifyIdentity(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setInfo(null);
    setSubmitting(true);
    try {
      // No CSRF token needed here — no session is authenticated yet, and
      // none of these activation steps authenticate one until the final
      // create-account call succeeds.
      const resp = await api.post<VerifyIdentityResponse>("/auth/activation/verify-identity", {
        mat_number: matNumber,
        utg_email: utgEmail,
      });
      setInfo(resp.detail);
      setStep("code");
    } catch (err) {
      if (isAlreadyActivated(err)) {
        setStep("already_activated");
      } else {
        setError(detailOf(err, "We could not verify your details. Please check your MAT number and UTG email address and try again."));
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function handleVerifyCode(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setInfo(null);
    setSubmitting(true);
    try {
      const resp = await api.post<VerifyCodeResponse>("/auth/activation/verify-code", {
        mat_number: matNumber,
        utg_email: utgEmail,
        code,
      });
      setVerificationToken(resp.verification_token);
      setStep("account");
    } catch (err) {
      if (isAlreadyActivated(err)) {
        setStep("already_activated");
      } else {
        setError(detailOf(err, "That code is incorrect or has expired. Please check it and try again, or request a new one."));
      }
      setCode("");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleResendCode() {
    setError(null);
    setInfo(null);
    setSubmitting(true);
    try {
      const resp = await api.post<ResendCodeResponse>("/auth/activation/resend-code", {
        mat_number: matNumber,
        utg_email: utgEmail,
      });
      setInfo(resp.detail);
      setCode("");
      setCooldown(RESEND_COOLDOWN_SECONDS);
    } catch (err) {
      if (isAlreadyActivated(err)) {
        setStep("already_activated");
      } else if (err instanceof ApiError && err.status === 429) {
        const retryAfter = typeof err.detail === "object" && err.detail && "retry_after_seconds" in (err.detail as any)
          ? (err.detail as any).retry_after_seconds
          : RESEND_COOLDOWN_SECONDS;
        setCooldown(retryAfter);
        setError(detailOf(err, "Please wait before requesting another code."));
      } else {
        setError(detailOf(err, "We could not resend your code. Please try again."));
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCreateAccount(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (password !== passwordConfirm) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await api.post<CreateAccountResponse>("/auth/activation/create-account", {
        verification_token: verificationToken,
        password,
        phone_number: phoneNumber,
        address,
        gender,
      });
      router.push("/dashboard");
    } catch (err) {
      if (isAlreadyActivated(err)) {
        setStep("already_activated");
      } else {
        setError(detailOf(err, "We could not finish activating your account. Please try again."));
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (step === "already_activated") {
    return (
      <div className="shell-narrow" style={{ maxWidth: 480, margin: "0 auto" }}>
        <Link href="/" className="back-link">
          <Icon name="chevron-left" size={15} />
          Back
        </Link>
        <h1>Account already activated</h1>
        <Alert tone="info">
          This account has already been activated. Please sign in, or use password recovery if you&apos;ve forgotten
          your password.
        </Alert>
        <Link href="/login" className="btn btn-primary btn-block" style={{ marginTop: "var(--space-4)" }}>
          Go to sign in
        </Link>
      </div>
    );
  }

  return (
    <div className="shell-narrow" style={{ maxWidth: 480, margin: "0 auto" }}>
      <Link href="/" className="back-link">
        <Icon name="chevron-left" size={15} />
        Back
      </Link>
      <h1>Activate your account</h1>
      <p className="muted">
        Verify your MAT number and UTG email, confirm the code we send you, then set a password.
      </p>

      <div className="split" style={{ marginBottom: "0.4rem" }}>
        <span className="muted">Step {STEP_NUMBER[step]} of 3</span>
      </div>
      <div
        className="progress-track"
        role="progressbar"
        aria-valuenow={STEP_NUMBER[step]}
        aria-valuemin={1}
        aria-valuemax={3}
        style={{ marginBottom: "var(--space-4)" }}
      >
        <div className="progress-fill" style={{ width: `${(STEP_NUMBER[step] / 3) * 100}%` }} />
      </div>

      {error && <Alert tone="error">{error}</Alert>}
      {!error && info && <Alert tone="info">{info}</Alert>}

      {step === "identity" && (
        <form onSubmit={handleVerifyIdentity}>
          <div className="form-section">
            <h3>Your identity</h3>
            <div className={`field${matNumberInvalid ? " has-error" : ""}`}>
              <label htmlFor="mat_number">MAT number</label>
              <input
                id="mat_number"
                required
                inputMode="numeric"
                maxLength={8}
                value={matNumber}
                onChange={(e) => setMatNumber(e.target.value.replace(/\D/g, ""))}
              />
              {matNumberInvalid ? (
                <span className="field-error">MAT number must be exactly 8 digits.</span>
              ) : (
                <span className="hint">Your 8-digit University of The Gambia matriculation number.</span>
              )}
            </div>
            <div className={`field${utgEmailInvalid ? " has-error" : ""}`} style={{ marginBottom: 0 }}>
              <label htmlFor="utg_email">UTG email address</label>
              <input
                id="utg_email"
                type="email"
                required
                autoComplete="email"
                value={utgEmail}
                onChange={(e) => setUtgEmail(e.target.value)}
              />
              {utgEmailInvalid ? (
                <span className="field-error">Please use your UTG email address (ending in {UTG_EMAIL_SUFFIX}).</span>
              ) : (
                <span className="hint">Must end in {UTG_EMAIL_SUFFIX}.</span>
              )}
            </div>
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={submitting || matNumberInvalid || utgEmailInvalid}>
            {submitting && <span className="spinner" />}
            {submitting ? "Verifying…" : "Verify identity"}
          </button>
        </form>
      )}

      {step === "code" && (
        <form onSubmit={handleVerifyCode}>
          <div className="form-section">
            <h3>Enter your code</h3>
            <div className="field" style={{ marginBottom: 0 }}>
              <label htmlFor="code">Verification code</label>
              <input
                id="code"
                required
                inputMode="numeric"
                minLength={6}
                maxLength={8}
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
              <span className="hint">Sent to {utgEmail}. Expires in 24 hours and can only be used once.</span>
            </div>
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={submitting || code.length < 6}>
            {submitting && <span className="spinner" />}
            {submitting ? "Checking…" : "Verify code"}
          </button>

          <button
            type="button"
            className="btn btn-secondary btn-block"
            style={{ marginTop: "var(--space-3)" }}
            disabled={submitting || cooldown > 0}
            onClick={handleResendCode}
          >
            {cooldown > 0 ? (
              <>
                <Icon name="clock" size={15} />
                Resend available in {cooldown}s
              </>
            ) : (
              "Resend code"
            )}
          </button>
        </form>
      )}

      {step === "account" && (
        <form onSubmit={handleCreateAccount}>
          <div className="form-section">
            <h3>Choose a password</h3>
            <div className="field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                required
                minLength={12}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <span className="hint">At least 12 characters.</span>
            </div>
            <div className={`field${passwordMismatch ? " has-error" : ""}`} style={{ marginBottom: 0 }}>
              <label htmlFor="password_confirm">Confirm password</label>
              <input
                id="password_confirm"
                type="password"
                required
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
              />
              {passwordMismatch && <span className="field-error">Passwords do not match.</span>}
            </div>
          </div>

          <div className="form-section">
            <h3>Profile details (optional)</h3>
            <div className="field">
              <label htmlFor="phone_number">Phone number</label>
              <input id="phone_number" value={phoneNumber} onChange={(e) => setPhoneNumber(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="address">Address</label>
              <input id="address" value={address} onChange={(e) => setAddress(e.target.value)} />
            </div>
            <div className="field" style={{ marginBottom: 0 }}>
              <label htmlFor="gender">Gender</label>
              <select id="gender" value={gender} onChange={(e) => setGender(e.target.value)}>
                <option value="">Prefer not to say</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
            {submitting && <span className="spinner" />}
            {submitting ? "Activating…" : "Activate account"}
          </button>
        </form>
      )}
    </div>
  );
}
