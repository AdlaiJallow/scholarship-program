import { ApplicationStatus, STATUS_LABELS } from "@/lib/types";
import { Icon, IconName } from "@/components/Icon";

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

const TONE_ICON: Record<"neutral" | "progress" | "good" | "bad", IconName> = {
  neutral: "clock",
  progress: "clock",
  good: "check-circle",
  bad: "alert-circle",
};

export function StatusPill({ status }: { status: ApplicationStatus }) {
  const tone = TONE[status] ?? "neutral";
  return (
    <span className={`pill pill-${tone}`}>
      <Icon name={TONE_ICON[tone]} size={12} />
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}
