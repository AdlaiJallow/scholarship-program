import Link from "next/link";

const STEPS = [
  {
    title: "Activate your account",
    body: "Verify your MAT number and UTG email, confirm the code we send you, then set a password.",
  },
  {
    title: "Upload your documents",
    body: "Submit each required document once — track exactly what's outstanding at a glance.",
  },
  {
    title: "Get verified",
    body: "A Ministry officer reviews your submission and notifies you the moment a decision is made.",
  },
];

export default function HomePage() {
  return (
    <div>
      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow">Ministry Scholarship Programme</span>
          <h1 className="text-display" style={{ margin: "0.5rem 0 1rem" }}>
            Verify your scholarship, entirely online.
          </h1>
          <p>
            No more in-person visits. Upload your documents, track every step of your verification, and
            receive your decision — all from one secure portal.
          </p>
          <div className="row">
            <Link className="btn btn-primary" href="/login">
              Sign in
            </Link>
            <Link className="btn btn-secondary" href="/activate">
              Activate your account
            </Link>
          </div>
        </div>
      </section>

      <hr className="divider" style={{ margin: "0 0 var(--space-8)" }} />

      <section>
        <h2 style={{ margin: "0 0 0.25rem" }}>How it works</h2>
        <p className="muted">Three steps from activation to a verified scholarship.</p>
        <div className="step-grid">
          {STEPS.map((step, i) => (
            <div className="step-card" key={step.title}>
              <span className="step-number">{i + 1}</span>
              <h3>{step.title}</h3>
              <p className="muted" style={{ marginBottom: 0 }}>{step.body}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
