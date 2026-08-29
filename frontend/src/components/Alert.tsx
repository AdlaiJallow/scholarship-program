import { Icon, IconName } from "@/components/Icon";

type AlertTone = "error" | "success" | "warning" | "info";

const TONE_ICON: Record<AlertTone, IconName> = {
  error: "alert-circle",
  success: "check-circle",
  warning: "alert-triangle",
  info: "info",
};

export function Alert({
  tone,
  title,
  children,
}: {
  tone: AlertTone;
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`alert alert-${tone}`} role={tone === "error" ? "alert" : "status"}>
      <Icon name={TONE_ICON[tone]} size={18} />
      <div>
        {title && <div className="alert-title">{title}</div>}
        <div>{children}</div>
      </div>
    </div>
  );
}
