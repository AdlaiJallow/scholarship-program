import { Icon, IconName } from "@/components/Icon";

export function EmptyState({
  icon = "inbox",
  title,
  description,
  action,
}: {
  icon?: IconName;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <Icon name={icon} size={22} />
      </span>
      <h3>{title}</h3>
      {description && <p className="muted" style={{ maxWidth: 380 }}>{description}</p>}
      {action}
    </div>
  );
}
