"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { Icon } from "@/components/Icon";

export function ConfirmDialog({
  title,
  description,
  tone = "primary",
  confirmLabel,
  cancelLabel = "Cancel",
  commentLabel,
  commentRequired,
  commentPlaceholder,
  busy,
  onConfirm,
  onCancel,
}: {
  title: string;
  description?: string;
  tone?: "primary" | "danger";
  confirmLabel: string;
  cancelLabel?: string;
  commentLabel?: string;
  commentRequired?: boolean;
  commentPlaceholder?: string;
  busy?: boolean;
  onConfirm: (comment: string) => void;
  onCancel: () => void;
}) {
  const [comment, setComment] = useState("");
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null;
    dialogRef.current?.querySelector<HTMLElement>("input, textarea, button")?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onCancel();
        return;
      }
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
        "button, input, textarea, select, a[href]"
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previouslyFocused?.focus();
    };
  }, [onCancel]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    onConfirm(comment);
  }

  const commentInvalid = Boolean(commentRequired && commentLabel && comment.trim() === "");

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onCancel();
      }}
    >
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="confirm-dialog-title" ref={dialogRef}>
        <div className="split" style={{ marginBottom: "0.5rem", alignItems: "flex-start" }}>
          <h2 id="confirm-dialog-title" style={{ margin: 0 }}>
            {title}
          </h2>
          <button type="button" className="btn-ghost" style={{ padding: "0.2rem" }} onClick={onCancel} aria-label="Close">
            <Icon name="x" size={18} />
          </button>
        </div>
        {description && <p className="muted">{description}</p>}
        <form onSubmit={handleSubmit} className="stack">
          {commentLabel && (
            <div className="field" style={{ marginBottom: 0 }}>
              <label htmlFor="confirm-dialog-comment">{commentLabel}</label>
              <textarea
                id="confirm-dialog-comment"
                rows={3}
                value={comment}
                placeholder={commentPlaceholder}
                onChange={(e) => setComment(e.target.value)}
                autoFocus
              />
            </div>
          )}
          <div className="row" style={{ justifyContent: "flex-end" }}>
            <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={busy}>
              {cancelLabel}
            </button>
            <button
              type="submit"
              className={`btn ${tone === "danger" ? "btn-danger" : "btn-primary"}`}
              disabled={busy || commentInvalid}
            >
              {busy && <span className="spinner" />}
              {confirmLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
