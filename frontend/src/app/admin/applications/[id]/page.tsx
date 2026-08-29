"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { ApplicationDetail, DocumentSlotStatus } from "@/lib/types";
import { StatusPill } from "@/components/StatusPill";
import { Icon } from "@/components/Icon";
import { Alert } from "@/components/Alert";
import { Timeline } from "@/components/Timeline";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { SkeletonCard } from "@/components/Skeleton";

const REJECTION_REASONS: { value: string; label: string }[] = [
  { value: "invalid_document", label: "Invalid document" },
  { value: "expired_document", label: "Expired document" },
  { value: "missing_document", label: "Missing document" },
  { value: "information_mismatch", label: "Information mismatch" },
  { value: "unclear_document", label: "Unclear document" },
  { value: "info_correction_needed", label: "Student information requires correction" },
  { value: "other", label: "Other" },
];

const REJECTION_LABEL = Object.fromEntries(REJECTION_REASONS.map((r) => [r.value, r.label]));

const DOC_VERDICT_COPY: Record<"needs_clarification" | "rejected", { title: string; confirmLabel: string }> = {
  needs_clarification: { title: "Request a correction on this document", confirmLabel: "Send request" },
  rejected: { title: "Reject this document", confirmLabel: "Reject document" },
};

export default function ApplicationReviewPage() {
  const params = useParams<{ id: string }>();
  const [application, setApplication] = useState<ApplicationDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [rejectReason, setRejectReason] = useState(REJECTION_REASONS[0].value);
  const [rejectDetail, setRejectDetail] = useState("");
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [pendingReject, setPendingReject] = useState<{ reason: string; detail: string } | null>(null);

  const [infoComment, setInfoComment] = useState("");
  const [flaggedSlots, setFlaggedSlots] = useState<number[]>([]);
  const [showInfoForm, setShowInfoForm] = useState(false);

  const [pendingApprove, setPendingApprove] = useState(false);
  const [pendingDocAction, setPendingDocAction] = useState<{ slotId: number; verdict: "needs_clarification" | "rejected" } | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await api.get<ApplicationDetail>(`/admin/applications/${params.id}`);
      setApplication(data);
      setError(null);
    } catch {
      setError("Could not load this application, or you do not have access to it.");
    }
  }, [params.id]);

  useEffect(() => {
    load();
  }, [load]);

  async function reviewDocument(slotId: number, verdict: DocumentSlotStatus, comment: string) {
    setBusy(true);
    try {
      await api.post(`/admin/applications/${params.id}/documents/${slotId}/review`, { verdict, comment });
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function handleClaim() {
    setBusy(true);
    try {
      await api.post(`/admin/applications/${params.id}/claim`);
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function runApprove() {
    setBusy(true);
    try {
      await api.post(`/admin/applications/${params.id}/approve`, { confirm: true, remarks: "" });
      setPendingApprove(false);
      await load();
    } finally {
      setBusy(false);
    }
  }

  function handleRejectFormSubmit(event: FormEvent) {
    event.preventDefault();
    setPendingReject({ reason: rejectReason, detail: rejectDetail });
  }

  async function runReject() {
    if (!pendingReject) return;
    setBusy(true);
    try {
      await api.post(`/admin/applications/${params.id}/reject`, {
        confirm: true,
        reason: pendingReject.reason,
        detail: pendingReject.detail,
      });
      setPendingReject(null);
      setShowRejectForm(false);
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function handleRequestInfo(event: FormEvent) {
    event.preventDefault();
    if (flaggedSlots.length === 0) return;
    setBusy(true);
    try {
      await api.post(`/admin/applications/${params.id}/request-information`, {
        submitted_document_ids: flaggedSlots,
        comment: infoComment,
      });
      setShowInfoForm(false);
      setFlaggedSlots([]);
      await load();
    } finally {
      setBusy(false);
    }
  }

  const backLink = (
    <Link href="/admin/queue" className="back-link">
      <Icon name="chevron-left" size={15} />
      Back to queue
    </Link>
  );

  if (error) {
    return (
      <div>
        {backLink}
        <Alert tone="error">{error}</Alert>
      </div>
    );
  }
  if (!application) {
    return (
      <div>
        {backLink}
        <div className="review-layout">
          <div className="stack">
            <SkeletonCard />
            <SkeletonCard />
          </div>
          <SkeletonCard />
        </div>
      </div>
    );
  }

  const canDecide = ["under_review", "resubmission_required"].includes(application.status);

  return (
    <div>
      {backLink}
      <div className="split" style={{ marginBottom: "var(--space-5)", alignItems: "flex-start" }}>
        <div>
          <span className="eyebrow">Application review</span>
          <h1 className="mono" style={{ margin: "0.2rem 0 0" }}>
            {application.reference_number || "Draft application"}
          </h1>
        </div>
      </div>

      <div className="review-layout">
        <div>
          <div className="card">
            <h2 style={{ marginTop: 0 }}>Student</h2>
            <p style={{ marginBottom: 0 }}>
              <strong>{application.student_name}</strong>
              <br />
              {application.student_email} · {application.student_phone}
              <br />
              DOB: {application.student_dob} · {application.student_gender}
            </p>
          </div>

          <div className="card">
            <h2 style={{ marginTop: 0 }}>Scholarship</h2>
            <p className="mono" style={{ marginBottom: "0.25rem" }}>
              {application.scholarship.scholarship_reference_id}
            </p>
            <p style={{ marginBottom: 0 }}>
              {application.scholarship.scholarship_type}
              <br />
              {application.scholarship.institution}, {application.scholarship.country}
              <br />
              {application.scholarship.program && <>Program: {application.scholarship.program}<br /></>}
              {application.scholarship.start_date} – {application.scholarship.end_date}
            </p>
          </div>

          <h2>Submitted documents</h2>
          {application.submitted_documents.map((slot) => (
            <div className="card" key={slot.id}>
              <div className="card-title-row">
                <strong>{slot.required_document.name}</strong>
                <span className={`pill pill-${slot.status === "verified" ? "good" : slot.status === "pending" ? "progress" : "bad"}`}>
                  {slot.status.replace("_", " ")}
                </span>
              </div>
              {slot.current_version ? (
                <>
                  <p className="muted row" style={{ gap: "0.4rem" }}>
                    <Icon name="file" size={14} />
                    {slot.current_version.original_filename} (v{slot.current_version.version_number}) — scan:{" "}
                    {slot.current_version.scan_status}
                  </p>
                  <div className="row">
                    <a className="btn btn-secondary" href={slot.current_version.download_url} target="_blank" rel="noreferrer">
                      <Icon name="download" size={15} />
                      Preview / download
                    </a>
                    {canDecide && (
                      <>
                        <button className="btn btn-secondary" disabled={busy} onClick={() => reviewDocument(slot.id, "verified", "")}>
                          <Icon name="check" size={15} />
                          Verify
                        </button>
                        <button
                          className="btn btn-secondary"
                          disabled={busy}
                          onClick={() => setPendingDocAction({ slotId: slot.id, verdict: "needs_clarification" })}
                        >
                          <Icon name="alert-triangle" size={15} />
                          Needs clarification
                        </button>
                        <button
                          className="btn btn-danger"
                          disabled={busy}
                          onClick={() => setPendingDocAction({ slotId: slot.id, verdict: "rejected" })}
                        >
                          <Icon name="x" size={15} />
                          Reject
                        </button>
                      </>
                    )}
                  </div>
                </>
              ) : (
                <p className="muted">Not yet uploaded.</p>
              )}
              {slot.reviews.length > 0 && (
                <ul className="muted" style={{ marginTop: "var(--space-3)" }}>
                  {slot.reviews.map((r) => (
                    <li key={r.id}>
                      {r.officer_name}: {r.verdict} {r.comment && `— ${r.comment}`}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}

          <h2>Status history</h2>
          <div className="card">
            <Timeline entries={application.status_history} />
          </div>
        </div>

        <div className="review-side stack">
          <div className="panel">
            <div className="split" style={{ marginBottom: application.assigned_officer ? 0 : "var(--space-4)" }}>
              <span className="muted">Status</span>
              <StatusPill status={application.status} />
            </div>
            {!application.assigned_officer && (
              <button type="button" className="btn btn-secondary btn-block" onClick={handleClaim} disabled={busy}>
                Claim this application
              </button>
            )}
          </div>

          {canDecide && (
            <div className="panel">
              <h2 style={{ marginTop: 0 }}>Decision</h2>
              <div className="stack" style={{ gap: "var(--space-2)" }}>
                <button className="btn btn-primary btn-block" disabled={busy} onClick={() => setPendingApprove(true)}>
                  <Icon name="check-circle" size={16} />
                  Approve
                </button>
                <button className="btn btn-danger btn-block" disabled={busy} onClick={() => setShowRejectForm((v) => !v)}>
                  Reject
                </button>
                <button className="btn btn-secondary btn-block" disabled={busy} onClick={() => setShowInfoForm((v) => !v)}>
                  Request additional information
                </button>
              </div>

              {showRejectForm && (
                <form onSubmit={handleRejectFormSubmit} className="stack" style={{ marginTop: "var(--space-4)" }}>
                  <div className="field">
                    <label htmlFor="reason">Rejection reason</label>
                    <select id="reason" value={rejectReason} onChange={(e) => setRejectReason(e.target.value)}>
                      {REJECTION_REASONS.map((r) => (
                        <option key={r.value} value={r.value}>
                          {r.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field" style={{ marginBottom: 0 }}>
                    <label htmlFor="detail">Details for the student</label>
                    <input id="detail" value={rejectDetail} onChange={(e) => setRejectDetail(e.target.value)} required />
                  </div>
                  <button type="submit" className="btn btn-danger btn-block" disabled={busy}>
                    Continue to confirm
                  </button>
                </form>
              )}

              {showInfoForm && (
                <form onSubmit={handleRequestInfo} className="stack" style={{ marginTop: "var(--space-4)" }}>
                  <p className="muted" style={{ marginBottom: 0 }}>Select the document(s) that need correction:</p>
                  {application.submitted_documents.map((slot) => (
                    <label key={slot.id} className="checkbox-row">
                      <input
                        type="checkbox"
                        checked={flaggedSlots.includes(slot.id)}
                        onChange={(e) =>
                          setFlaggedSlots((prev) =>
                            e.target.checked ? [...prev, slot.id] : prev.filter((id) => id !== slot.id)
                          )
                        }
                      />
                      {slot.required_document.name}
                    </label>
                  ))}
                  <div className="field" style={{ marginBottom: 0 }}>
                    <label htmlFor="comment">Message to the student</label>
                    <input id="comment" value={infoComment} onChange={(e) => setInfoComment(e.target.value)} required />
                  </div>
                  <button type="submit" className="btn btn-secondary btn-block" disabled={busy || flaggedSlots.length === 0}>
                    Send request
                  </button>
                </form>
              )}
            </div>
          )}
        </div>
      </div>

      {pendingApprove && (
        <ConfirmDialog
          title="Approve this application?"
          description="The student will be notified immediately."
          confirmLabel="Approve"
          tone="primary"
          busy={busy}
          onConfirm={runApprove}
          onCancel={() => setPendingApprove(false)}
        />
      )}

      {pendingReject && (
        <ConfirmDialog
          title="Reject this application?"
          description={`Reason: ${REJECTION_LABEL[pendingReject.reason]}. This will be visible to the student along with: "${pendingReject.detail}"`}
          confirmLabel="Confirm rejection"
          tone="danger"
          busy={busy}
          onConfirm={runReject}
          onCancel={() => setPendingReject(null)}
        />
      )}

      {pendingDocAction && (
        <ConfirmDialog
          title={DOC_VERDICT_COPY[pendingDocAction.verdict].title}
          confirmLabel={DOC_VERDICT_COPY[pendingDocAction.verdict].confirmLabel}
          tone={pendingDocAction.verdict === "rejected" ? "danger" : "primary"}
          commentLabel="Comment for the student"
          commentRequired
          commentPlaceholder="Explain what needs to change…"
          busy={busy}
          onConfirm={(comment) => {
            reviewDocument(pendingDocAction.slotId, pendingDocAction.verdict, comment);
            setPendingDocAction(null);
          }}
          onCancel={() => setPendingDocAction(null)}
        />
      )}
    </div>
  );
}
