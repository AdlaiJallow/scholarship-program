import { ApplicationStatus, STATUS_LABELS } from "@/lib/types";

const TONE: Record<ApplicationStatus, "neutral" | "progress" | "good" | "bad"> = {
  not_started: "neutral",
  in_progress: "progress",
  submitted: "progress",
  under_review: "progress",
  additional_info_required: "bad",
  approved: "good",
  rejected: "bad",
  resubmission_required: "bad",
};

export function StatusPill({ status }: { status: ApplicationStatus }) {
  const tone = TONE[status] ?? "neutral";
  return <span className={`pill pill-${tone}`}>{STATUS_LABELS[status] ?? status}</span>;
}
