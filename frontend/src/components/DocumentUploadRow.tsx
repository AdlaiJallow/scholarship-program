"use client";

import { useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { RequirementRow } from "@/lib/types";

const SLOT_LABEL: Record<string, { label: string; tone: "neutral" | "progress" | "good" | "bad" }> = {
  pending: { label: "Pending review", tone: "progress" },
  verified: { label: "Accepted", tone: "good" },
  rejected: { label: "Rejected", tone: "bad" },
  needs_clarification: { label: "Needs correction", tone: "bad" },
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

  return (
    <div className="card" style={{ marginBottom: "0.75rem" }}>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div>
          <strong>{doc.name}</strong>
          {doc.is_mandatory && <span className="muted"> (required)</span>}
          {doc.description && <p className="muted">{doc.description}</p>}
        </div>
        {statusMeta && <span className={`pill pill-${statusMeta.tone}`}>{statusMeta.label}</span>}
      </div>

      {submitted?.current_version && (
        <p className="muted">
          Uploaded: {submitted.current_version.original_filename} (v{submitted.current_version.version_number})
        </p>
      )}

      {submitted?.reviews.some((r) => r.comment) && (
        <div className="error-banner" style={{ marginTop: "0.5rem" }}>
          {submitted.reviews
            .filter((r) => r.comment)
            .map((r) => (
              <div key={r.id}>{r.comment}</div>
            ))}
        </div>
      )}

      {error && <div className="error-banner">{error}</div>}

      {editable && (
        <div className="row" style={{ marginTop: "0.6rem" }}>
          <input
            ref={fileInput}
            type="file"
            accept={doc.accepted_file_types.map((t) => `.${t}`).join(",")}
            onChange={handleFileChange}
            disabled={uploading}
          />
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
