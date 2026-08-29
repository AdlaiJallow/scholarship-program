import { StatusHistoryEntry } from "@/lib/types";

export function Timeline({ entries }: { entries: StatusHistoryEntry[] }) {
  return (
    <ol className="timeline">
      {entries.map((h, i) => (
        <li className="timeline-item" key={i}>
          <span className="timeline-dot" />
          <div>
            {h.from_status || "—"} → <strong>{h.to_status}</strong>
          </div>
          {h.note && <div className="muted">{h.note}</div>}
          <div className="timeline-time">{new Date(h.created_at).toLocaleString()}</div>
        </li>
      ))}
    </ol>
  );
}
