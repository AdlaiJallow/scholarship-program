"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { RequirementsResponse, StudentProfile } from "@/lib/types";
import { StatusPill } from "@/components/StatusPill";
import { DocumentUploadRow } from "@/components/DocumentUploadRow";
import { ProgressBar } from "@/components/ProgressBar";
import { Alert } from "@/components/Alert";
import { SkeletonCard } from "@/components/Skeleton";

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
    return <Alert tone="error">{loadError}</Alert>;
  }

  if (!profile || !requirements) {
    return (
      <div className="stack">
        <div className="skeleton" style={{ width: "40%", height: "1.7rem" }} />
        <div className="skeleton" style={{ width: "60%", height: "1rem" }} />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  const editable = EDITABLE_STATUSES.has(requirements.application_status);
  const mandatoryDocs = requirements.requirements.filter((r) => r.required_document.is_mandatory);
  const mandatoryOutstanding = mandatoryDocs.filter((r) => !r.submitted?.current_version);
  const mandatoryDone = mandatoryDocs.length - mandatoryOutstanding.length;

  return (
    <div>
      <div className="split" style={{ alignItems: "flex-start", marginBottom: "var(--space-2)" }}>
        <div>
          <span className="eyebrow">Your application</span>
          <h1 style={{ margin: "0.2rem 0 0" }}>Welcome, {profile.full_name}</h1>
        </div>
        <StatusPill status={requirements.application_status} />
      </div>

      <div className="panel" style={{ marginBottom: "var(--space-6)" }}>
        <ProgressBar done={mandatoryDone} total={mandatoryDocs.length} />
      </div>

      {requirements.application_status === "additional_info_required" && (
        <Alert tone="warning" title="Action needed">
          The Ministry needs corrections on one or more documents below before your application can proceed.
        </Alert>
      )}

      <h2>Required documents</h2>
      <div className="stack">
        {requirements.requirements.map((row) => (
          <DocumentUploadRow key={row.required_document.id} row={row} editable={editable} onChanged={load} />
        ))}
      </div>

      {editable && (
        <div className="panel" style={{ marginTop: "var(--space-6)", borderColor: "var(--teal-tint-strong)" }}>
          {submitError && <Alert tone="error">{submitError}</Alert>}
          {mandatoryOutstanding.length > 0 ? (
            <p className="muted" style={{ marginBottom: "var(--space-4)" }}>
              Upload all required documents before submitting: {mandatoryOutstanding.map((r) => r.required_document.name).join(", ")}.
            </p>
          ) : (
            <p style={{ marginBottom: "var(--space-4)" }}>
              By submitting, you confirm the information and documents above are accurate and complete.
            </p>
          )}
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={submitting || mandatoryOutstanding.length > 0}
          >
            {submitting && <span className="spinner" />}
            {submitting ? "Submitting…" : "Submit for verification"}
          </button>
        </div>
      )}
    </div>
  );
}
