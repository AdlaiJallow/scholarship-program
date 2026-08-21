"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { ApplicationDetail, DocumentSlotStatus } from "@/lib/types";
import { StatusPill } from "@/components/StatusPill";

const REJECTION_REASONS: { value: string; label: string }[] = [
  { value: "invalid_document", label: "Invalid document" },
  { value: "expired_document", label: "Expired document" },
  { value: "missing_document", label: "Missing document" },
  { value: "information_mismatch", label: "Information mismatch" },
  { value: "unclear_document", label: "Unclear document" },
  { value: "info_correction_needed", label: "Student information requires correction" },
  { value: "other", label: "Other" },
];

export default function ApplicationReviewPage() {
  const params = useParams<{ id: string }>();
  const [application, setApplication] = useState<ApplicationDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [rejectReason, setRejectReason] = useState(REJECTION_REASONS[0].value);
  const [rejectDetail, setRejectDetail] = useState("");
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [infoComment, setInfoComment] = useState("");
  const [flaggedSlots, setFlaggedSlots] = useState<number[]>([]);
  const [showInfoForm, setShowInfoForm] = useState(false);

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

  async function handleApprove() {
    if (!window.confirm("Approve this application? The student will be notified immediately.")) return;
    setBusy(true);
    try {
      await api.post(`/admin/applications/${params.id}/approve`, { confirm: true, remarks: "" });
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function handleReject(event: FormEvent) {
    event.preventDefault();
    if (!window.confirm("Reject this application? The reason will be visible to the student.")) return;
    setBusy(true);
    try {
      await api.post(`/admin/applications/${params.id}/reject`, {
        confirm: true,
        reason: rejectReason,
        detail: rejectDetail,
      });
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

  if (error) return <div className="error-banner">{error}</div>;
  if (!application) return <p className="muted">Loading…</p>;

  const canDecide = ["under_review", "resubmission_required"].includes(application.status);

  return (
    <div className="stack">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>{application.reference_number || "Draft application"}</h1>
        <StatusPill status={application.status} />
      </div>

      {!application.assigned_officer && (
        <button type="button" className="btn btn-secondary" onClick={handleClaim} disabled={busy}>
          Claim this application
        </button>
      )}

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Student</h2>
        <p>
          <strong>{application.student_name}</strong>
          <br />
          {application.student_email} · {application.student_phone}
          <br />
          DOB: {application.student_dob} · {application.student_gender}
        </p>
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Scholarship</h2>
        <p>
          {application.scholarship.scholarship_reference_id} — {application.scholarship.scholarship_type}
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
          <div className="row" style={{ justifyContent: "space-between" }}>
            <strong>{slot.required_document.name}</strong>
            <span className={`pill pill-${slot.status === "verified" ? "good" : slot.status === "pending" ? "progress" : "bad"}`}>
              {slot.status.replace("_", " ")}
            </span>
          </div>
          {slot.current_version ? (
            <>
              <p className="muted">
                {slot.current_version.original_filename} (v{slot.current_version.version_number}) — scan:{" "}
                {slot.current_version.scan_status}
              </p>
              <a className="btn btn-secondary" href={slot.current_version.download_url} target="_blank" rel="noreferrer">
                Preview / download
              </a>
              {canDecide && (
                <div className="row" style={{ marginTop: "0.6rem" }}>
                  <button className="btn btn-secondary" disabled={busy} onClick={() => reviewDocument(slot.id, "verified", "")}>
                    Verify
                  </button>
                  <button
                    className="btn btn-secondary"
                    disabled={busy}
                    onClick={() => {
                      const comment = window.prompt("Reason this document needs clarification:") ?? "";
                      reviewDocument(slot.id, "needs_clarification", comment);
                    }}
                  >
                    Needs clarification
                  </button>
                  <button
                    className="btn btn-danger"
                    disabled={busy}
                    onClick={() => {
                      const comment = window.prompt("Reason for rejecting this document:") ?? "";
                      reviewDocument(slot.id, "rejected", comment);
                    }}
                  >
                    Reject
                  </button>
                </div>
              )}
            </>
          ) : (
            <p className="muted">Not yet uploaded.</p>
          )}
          {slot.reviews.length > 0 && (
            <ul className="muted">
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
        <ul className="muted" style={{ margin: 0, paddingLeft: "1.1rem" }}>
          {application.status_history.map((h, i) => (
            <li key={i}>
              {h.from_status || "—"} → {h.to_status} {h.note && `(${h.note})`} —{" "}
              {new Date(h.created_at).toLocaleString()}
            </li>
          ))}
        </ul>
      </div>

      {canDecide && (
        <div className="card">
          <h2 style={{ marginTop: 0 }}>Decision</h2>
          <div className="row">
            <button className="btn btn-primary" disabled={busy} onClick={handleApprove}>
              Approve
            </button>
            <button className="btn btn-danger" disabled={busy} onClick={() => setShowRejectForm((v) => !v)}>
              Reject
            </button>
            <button className="btn btn-secondary" disabled={busy} onClick={() => setShowInfoForm((v) => !v)}>
              Request additional information
            </button>
          </div>

          {showRejectForm && (
            <form onSubmit={handleReject} className="stack" style={{ marginTop: "1rem" }}>
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
              <div className="field">
                <label htmlFor="detail">Details for the student</label>
                <input id="detail" value={rejectDetail} onChange={(e) => setRejectDetail(e.target.value)} required />
              </div>
              <button type="submit" className="btn btn-danger" disabled={busy}>
                Confirm rejection
              </button>
            </form>
          )}

          {showInfoForm && (
            <form onSubmit={handleRequestInfo} className="stack" style={{ marginTop: "1rem" }}>
              <p className="muted">Select the document(s) that need correction:</p>
              {application.submitted_documents.map((slot) => (
                <label key={slot.id} className="row">
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
              <div className="field">
                <label htmlFor="comment">Message to the student</label>
                <input id="comment" value={infoComment} onChange={(e) => setInfoComment(e.target.value)} required />
              </div>
              <button type="submit" className="btn btn-secondary" disabled={busy || flaggedSlots.length === 0}>
                Send request
              </button>
            </form>
          )}
        </div>
      )}
    </div>
  );
}
