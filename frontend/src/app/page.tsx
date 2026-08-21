import Link from "next/link";

export default function HomePage() {
  return (
    <div className="stack">
      <h1>Scholarship Verification Portal</h1>
      <p>
        Verify your scholarship documents online — no need to visit the Ministry in person. Track your
        application status, upload documents, and receive decisions directly through this portal.
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
  );
}
