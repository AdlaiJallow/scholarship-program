"use client";

import { useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { RequirementRow } from "@/lib/types";
import { Icon, IconName } from "@/components/Icon";
import { Alert } from "@/components/Alert";

const SLOT_LABEL: Record<string, { label: string; tone: "neutral" | "progress" | "good" | "bad"; icon: IconName }> = {
  pending: { label: "Pending review", tone: "progress", icon: "clock" },
  verified: { label: "Accepted", tone: "good", icon: "check-circle" },
  rejected: { label: "Rejected", tone: "bad", icon: "alert-circle" },
  needs_clarification: { label: "Needs correction", tone: "bad", icon: "alert-triangle" },
};

export function DocumentUploadRow({
  row,
  editable,
  onChanged,
}: {
  row: RequirementRow;
  editable: boolean;
  onChanged: () => void;
}) {
  const { required_document: doc, submitted } = row;
  const fileInput = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleFileChange() {
    const file = fileInput.current?.files?.[0];
    if (!file) return;

    setError(null);
    if (file.size > doc.max_file_size_bytes) {
      setError(
        `This file is ${(file.size / (1024 * 1024)).toFixed(1)}MB; the limit for ${doc.name} is ${(
          doc.max_file_size_bytes /
          (1024 * 1024)
        ).toFixed(1)}MB.`
      );
      if (fileInput.current) fileInput.current.value = "";
      return;
    }

    const form = new FormData();
    form.append("required_document_id", String(doc.id));
    form.append("file", file);

    setUploading(true);
    try {
      await api.postForm("/me/documents", form);
      onChanged();
    } catch (err) {
      if (err instanceof ApiError && typeof err.detail === "object" && err.detail && "detail" in (err.detail as any)) {
        setError((err.detail as any).detail);
      } else {
        setError("Upload failed. Please try again.");
      }
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function handleDelete() {
    if (!submitted) return;
    await api.del(`/me/documents/${submitted.id}`);
    onChanged();
  }

  const statusMeta = submitted ? SLOT_LABEL[submitted.status] : null;
  const accept = doc.accepted_file_types.map((t) => `.${t}`).join(",");
  const maxSizeMb = (doc.max_file_size_bytes / (1024 * 1024)).toFixed(0);

  return (
    <div className="card">
      <div className="card-title-row">
        <div>
          <strong>{doc.name}</strong>
          {doc.is_mandatory && <span className="muted"> (required)</span>}
          {doc.description && <p className="muted" style={{ marginTop: "0.2rem", marginBottom: 0 }}>{doc.description}</p>}
        </div>
        {statusMeta && (
          <span className={`pill pill-${statusMeta.tone}`}>
            <Icon name={statusMeta.icon} size={12} />
            {statusMeta.label}
          </span>
        )}
      </div>

      {submitted?.current_version && (
        <p className="muted row" style={{ gap: "0.4rem" }}>
          <Icon name="file" size={14} />
          {submitted.current_version.original_filename} (v{submitted.current_version.version_number})
        </p>
      )}

      {submitted?.reviews.some((r) => r.comment) && (
        <Alert tone="warning" title="Correction requested">
          {submitted.reviews
            .filter((r) => r.comment)
            .map((r) => (
              <div key={r.id}>{r.comment}</div>
            ))}
        </Alert>
      )}

      {error && (
        <Alert tone="error">
          {error}
        </Alert>
      )}

      {editable && (
        <div className="row" style={{ marginTop: "0.75rem", alignItems: "stretch" }}>
          <label className="dropzone" style={{ flex: 1, minWidth: 200 }}>
            <input ref={fileInput} type="file" accept={accept} onChange={handleFileChange} disabled={uploading} />
            {uploading ? (
              <>
                <span className="spinner" style={{ display: "block", margin: "0 auto 0.4rem" }} />
                Uploading…
              </>
            ) : (
              <>
                <Icon name="upload" size={18} />
                <div>{submitted ? "Replace file" : "Choose a file"} or drop it here</div>
                <div className="muted" style={{ fontSize: "0.75rem" }}>
                  {doc.accepted_file_types.join(", ").toUpperCase()} · up to {maxSizeMb}MB
                </div>
              </>
            )}
          </label>
          {submitted && (
            <button type="button" className="btn btn-secondary" onClick={handleDelete} disabled={uploading}>
              Remove
            </button>
          )}
        </div>
      )}
    </div>
  );
}
