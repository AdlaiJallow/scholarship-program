export function Skeleton({ width = "100%", height = "1rem", style }: { width?: string | number; height?: string | number; style?: React.CSSProperties }) {
  return <div className="skeleton" style={{ width, height, ...style }} />;
}

export function SkeletonCard() {
  return (
    <div className="card">
      <Skeleton width="40%" height="0.9rem" style={{ marginBottom: "0.75rem" }} />
      <Skeleton width="90%" height="0.8rem" style={{ marginBottom: "0.5rem" }} />
      <Skeleton width="70%" height="0.8rem" />
    </div>
  );
}
