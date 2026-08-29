export function ProgressBar({ done, total }: { done: number; total: number }) {
  const pct = total === 0 ? 100 : Math.round((done / total) * 100);
  return (
    <div>
      <div className="split" style={{ marginBottom: "0.4rem" }}>
        <span className="muted">
          {done} of {total} required documents submitted
        </span>
        <span className="muted" style={{ fontWeight: 600, color: "var(--ink-900)" }}>
          {pct}%
        </span>
      </div>
      <div className="progress-track" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className="progress-fill" data-complete={pct === 100} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
