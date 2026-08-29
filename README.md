# Scholarship Self-Verification & Approval Portal

A digital replacement for in-person scholarship-holder verification at a Ministry
scholarship department in The Gambia: students verify themselves and upload
documents online; Ministry officers review, approve, reject, or request
corrections; the Ministry remains the sole authority on every decision.

The full technical/product specification — architecture, ERD, security model,
RBAC, MVP/Phase 2/Phase 3 scope, and a critical risk register — was produced
first and is not duplicated here; see the published specification artifact
from this project's design phase.

## Repository layout

```
backend/    Django + Django REST Framework API (source of truth for the domain model and workflow)
frontend/   Next.js + TypeScript student and Ministry portals
infra/sql/  One-off database hardening scripts (audit-log immutability grants)
docker-compose.yml   Local multi-service stack: Postgres, Redis, MinIO, API, Celery worker, frontend
```

## What's implemented (MVP scope)

- Student self-verification workflow: activation → dynamic document checklist →
  upload with versioning → guided submission → status tracking → resubmission
  after Ministry-requested corrections.
- Ministry review workflow: queue with search/filter, per-document review,
  confirmed approve/reject/request-information, officer assignment and
  reassignment, RBAC across four roles (Super Administrator, Verification
  Officer, Supervisor, Read-Only/Reporting Officer).
- Identity verification via Ministry pre-registration + one-time activation
  code (system specification §11, Option A+B) — no open self-registration.
- Append-only audit logging, in-app notification center, email notifications
  (console backend in dev), Excel/CSV export, basic reporting endpoints.
- Document security: content-sniffed file validation, size limits,
  malware-scan pipeline (pluggable; ClamAV in production), authorized-only
  document access via signed/streamed downloads — never a public media URL.

Deliberately out of scope for MVP (see specification §23): automated
application assignment, SMS/WhatsApp notifications, OIDC/national-ID SSO,
identity-matching registration, renewals/payments.

## Backend — local development

Requires Python 3.11+ and PostgreSQL (or use the SQLite dev shortcut below).

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # or use uv
pip install -r requirements.txt
cp .env.example .env   # fill in FIELD_ENCRYPTION_KEY at minimum — see the comment in .env.example

# Fastest path to a running server without Postgres/Redis/MinIO installed:
export DJANGO_TEST_SQLITE=true CELERY_TASK_ALWAYS_EAGER=true DJANGO_EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

python manage.py migrate
python manage.py seed_demo_data   # creates a super admin, an officer, and a demo student pre-registration
python manage.py runserver
```

`seed_demo_data` prints the demo accounts' credentials and the demo
student's activation code to the console — use those to exercise the full
workflow through the API or frontend.

For demos/presentations, `python manage.py seed_investor_demo` builds on
top of `seed_demo_data` and populates five more scholarship holders spread
across every stage of the pipeline (in progress, under review, additional
info requested, rejected, approved) plus a second officer, so the queue,
dashboards, notifications, and audit log all have realistic content to
show. It prints all the demo accounts' credentials on completion.

Run the test suite (covers the full activation → upload → submit →
review → approve/reject/request-info workflow, plus the RBAC and
terminal-state guards):

```bash
DJANGO_TEST_SQLITE=true python manage.py test
```

In production, set `DOCUMENT_STORAGE_BACKEND=s3` (MinIO or AWS S3),
`ANTIVIRUS_SCAN_BACKEND=clamav`, and run `infra/sql/audit_immutability.sql`
against the database once, as described in that file's header.

## Frontend — local development

Requires Node.js 20+.

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev   # http://localhost:3000, expects the API at NEXT_PUBLIC_API_BASE_URL
```

## Full stack via Docker Compose

```bash
cp backend/.env.example backend/.env      # fill in real values before production use
cp frontend/.env.example frontend/.env.local
docker compose up --build
```

This brings up Postgres, Redis, MinIO, the Django API, a Celery worker, and
the Next.js frontend together. Run migrations and the demo seed inside the
`api` container on first boot:

```bash
docker compose exec api python manage.py migrate
docker compose exec api python manage.py seed_demo_data
```

## Security notes for anyone deploying this

- `FIELD_ENCRYPTION_KEY`, `DJANGO_SECRET_KEY`, and all credentials in
  `.env` must be real, unique secrets in any non-local environment — the
  checked-in defaults are for local development only.
- `ANTIVIRUS_SCAN_BACKEND` defaults to `noop` and logs a loud warning on
  every upload when set that way. Set it to `clamav` (with a reachable
  ClamAV daemon) before accepting real uploads from the public internet.
- Uploaded documents are never served from a public path; every access
  goes through an authorized API endpoint (`apps.verification.views.DocumentDownloadView`).
