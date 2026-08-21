"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { RequirementsResponse, StudentProfile } from "@/lib/types";
import { StatusPill } from "@/components/StatusPill";
import { DocumentUploadRow } from "@/components/DocumentUploadRow";

const EDITABLE_STATUSES = new Set(["not_started", "in_progress", "additional_info_required", "resubmission_required"]);

export default function DashboardPage() {
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [requirements, setRequirements] = useState<RequirementsResponse | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    try {
      const [profileData, requirementsData] = await Promise.all([
        api.get<StudentProfile>("/me/profile"),
        api.get<RequirementsResponse>("/me/requirements"),
      ]);
      setProfile(profileData);
      setRequirements(requirementsData);
      setLoadError(null);
    } catch (err) {
      setLoadError(err instanceof ApiError && err.status === 401 ? "Please sign in to view your dashboard." : "Could not load your dashboard.");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSubmit() {
    setSubmitError(null);
    setSubmitting(true);
    try {
      await api.post("/me/application/submit");
      await load();
    } catch (err) {
      if (err instanceof ApiError && typeof err.detail === "object" && err.detail && "detail" in (err.detail as any)) {
        setSubmitError((err.detail as any).detail);
      } else {
        setSubmitError("Could not submit your application. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (loadError) {
    return <div className="error-banner">{loadError}</div>;
  }

  if (!profile || !requirements) {
    return <p className="muted">Loading…</p>;
  }

  const editable = EDITABLE_STATUSES.has(requirements.application_status);
  const mandatoryOutstanding = requirements.requirements.filter(
    (r) => r.required_document.is_mandatory && !r.submitted?.current_version
  );

  return (
    <div className="stack">
      <h1>Welcome, {profile.full_name}</h1>
      <div className="row" style={{ alignItems: "center" }}>
        <span className="muted">Verification status:</span>
        <StatusPill status={requirements.application_status} />
      </div>

      {requirements.application_status === "additional_info_required" && (
        <div className="error-banner">
          The Ministry needs corrections on one or more documents below before your application can proceed.
        </div>
      )}

      <h2>Required documents</h2>
      <div>
        {requirements.requirements.map((row) => (
          <DocumentUploadRow key={row.required_document.id} row={row} editable={editable} onChanged={load} />
        ))}
      </div>

      {editable && (
        <div className="card">
          {submitError && <div className="error-banner">{submitError}</div>}
          {mandatoryOutstanding.length > 0 ? (
            <p className="muted">
              Upload all required documents before submitting: {mandatoryOutstanding.map((r) => r.required_document.name).join(", ")}.
            </p>
          ) : (
            <p className="muted">
              By submitting, you confirm the information and documents above are accurate and complete.
            </p>
          )}
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={submitting || mandatoryOutstanding.length > 0}
          >
            {submitting ? "Submitting…" : "Submit for verification"}
          </button>
        </div>
      )}
    </div>
  );
}
