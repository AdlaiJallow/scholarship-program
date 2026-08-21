"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";

export default function ActivatePage() {
  const router = useRouter();
  const [form, setForm] = useState({
    scholarship_id: "",
    date_of_birth: "",
    verification_code: "",
    password: "",
    password_confirm: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function update<K extends keyof typeof form>(key: K, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (form.password !== form.password_confirm) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      // Activation needs no CSRF token (DRF only enforces CSRF once a
      // session is already authenticated) and its response sets a fresh
      // csrftoken cookie that every request after this one will use.
      await api.post("/auth/activate", {
        scholarship_id: form.scholarship_id,
        date_of_birth: form.date_of_birth,
        verification_code: form.verification_code,
        password: form.password,
      });
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError && typeof err.detail === "object" && err.detail && "detail" in (err.detail as any)) {
        setError((err.detail as any).detail);
      } else {
        setError("We could not activate your account with those details. Please check them and try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="stack" style={{ maxWidth: 460 }}>
      <h1>Activate your account</h1>
      <p className="muted">
        Use the scholarship ID, date of birth, and one-time activation code the Ministry gave you.
      </p>
      {error && <div className="error-banner">{error}</div>}
      <form className="card" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="scholarship_id">Scholarship ID</label>
          <input
            id="scholarship_id"
            required
            value={form.scholarship_id}
            onChange={(e) => update("scholarship_id", e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="dob">Date of birth</label>
          <input
            id="dob"
            type="date"
            required
            value={form.date_of_birth}
            onChange={(e) => update("date_of_birth", e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="code">Activation code</label>
          <input
            id="code"
            required
            value={form.verification_code}
            onChange={(e) => update("verification_code", e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="password">Choose a password</label>
          <input
            id="password"
            type="password"
            required
            minLength={12}
            value={form.password}
            onChange={(e) => update("password", e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="password_confirm">Confirm password</label>
          <input
            id="password_confirm"
            type="password"
            required
            value={form.password_confirm}
            onChange={(e) => update("password_confirm", e.target.value)}
          />
        </div>
        <button type="submit" className="btn btn-primary" disabled={submitting} style={{ width: "100%" }}>
          {submitting ? "Activating…" : "Activate account"}
        </button>
      </form>
    </div>
  );
}
