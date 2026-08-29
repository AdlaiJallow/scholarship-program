"""
End-to-end coverage of the verification workflow (system specification §5,
§8, §9): activation → upload → submit → additional-info → resubmit →
approve, plus the RBAC/terminal-state guards. This mirrors a manual smoke
test run against a live server that caught two real bugs during
development (an integer-vs-UUID URL converter mismatch on document review,
and the requirements endpoint silently starting a new draft application
after a decision was already made) — kept here as a regression test so
neither regresses silently.
"""

import re
from datetime import date

from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.accounts.models import Officer, Role, StudentPreRegistration
from apps.catalog.models import Country, Institution, Program, ScholarshipType
from apps.scholarships.models import Scholarship
from apps.verification.models import Application, RequiredDocument

PDF_BYTES = b"%PDF-1.4\n%test document\n"


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, DOCUMENT_STORAGE_BACKEND="filesystem")
class VerificationWorkflowTests(APITestCase):
    def setUp(self):
        # ScopedRateThrottle state lives in the cache, not the DB, so it
        # isn't reset by the per-test transaction rollback.
        cache.clear()
        country = Country.objects.create(name="Senegal", iso_code="SEN")
        institution = Institution.objects.create(name="UCAD", country=country)
        program = Program.objects.create(
            name="Nursing", institution=institution, academic_level=Program.AcademicLevel.UNDERGRADUATE
        )
        scholarship_type = ScholarshipType.objects.create(name="Merit")

        self.scholarship = Scholarship.objects.create(
            scholarship_reference_id="20260001",
            scholarship_type=scholarship_type,
            institution=institution,
            country=country,
            program=program,
            start_date=date(2024, 9, 1),
            end_date=date(2027, 8, 31),
        )

        self.required_doc = RequiredDocument.objects.create(
            name="Transcript",
            is_mandatory=True,
            accepted_file_types=["pdf"],
            max_file_size_bytes=5 * 1024 * 1024,
        )

        self.pre_reg = StudentPreRegistration.objects.create(
            mat_number="20260001",
            full_name="Test Student",
            date_of_birth=date(2002, 1, 1),
            email="student@utg.edu.gm",
        )

        # "Verification Officer" and its permissions are seeded by
        # accounts.migrations.0002_seed_roles_permissions (system
        # specification §12), so we reuse it rather than recreate it.
        officer_role = Role.objects.get(name="Verification Officer")

        from apps.accounts.models import User

        officer_user = User.objects.create_user(
            email="officer@example.com", password="pw", user_type=User.UserType.OFFICER, is_active=True
        )
        self.officer = Officer.objects.create(
            user=officer_user, full_name="Officer", employee_id="OFF-1", role=officer_role
        )

    def _activate(self):
        resp = self.client.post(
            "/api/v1/auth/activation/verify-identity",
            {"mat_number": "20260001", "utg_email": "student@utg.edu.gm"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        code = re.search(r"code is: (\d+)", mail.outbox[-1].body).group(1)

        resp = self.client.post(
            "/api/v1/auth/activation/verify-code",
            {"mat_number": "20260001", "utg_email": "student@utg.edu.gm", "code": code},
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        token = resp.json()["verification_token"]

        resp = self.client.post(
            "/api/v1/auth/activation/create-account",
            {"verification_token": token, "password": "SuperSecret123!"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)

    def _student_user(self):
        self.pre_reg.refresh_from_db()
        return self.pre_reg.activated_student.user

    def _upload(self):
        upload = SimpleUploadedFile("transcript.pdf", PDF_BYTES, content_type="application/pdf")
        resp = self.client.post(
            "/api/v1/me/documents",
            {"required_document_id": self.required_doc.id, "file": upload},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        return resp.data

    def test_full_workflow_activation_through_approval(self):
        self._activate()
        self._upload()

        submit_resp = self.client.post("/api/v1/me/application/submit")
        self.assertEqual(submit_resp.status_code, 200, submit_resp.content)
        self.assertEqual(submit_resp.data["status"], "under_review")
        application_id = submit_resp.data["id"]

        self.client.force_authenticate(user=self.officer.user)

        detail = self.client.get(f"/api/v1/admin/applications/{application_id}")
        self.assertEqual(detail.status_code, 200)
        slot_id = detail.data["submitted_documents"][0]["id"]

        review_resp = self.client.post(
            f"/api/v1/admin/applications/{application_id}/documents/{slot_id}/review",
            {"verdict": "verified", "comment": "OK"},
            format="json",
        )
        self.assertEqual(review_resp.status_code, 201, review_resp.content)

        approve_resp = self.client.post(
            f"/api/v1/admin/applications/{application_id}/approve",
            {"remarks": "Good", "confirm": True},
            format="json",
        )
        self.assertEqual(approve_resp.status_code, 200)
        self.assertEqual(approve_resp.data["status"], "approved")

    def test_requirements_view_does_not_spawn_new_application_after_decision(self):
        """Regression test: previously calling /me/requirements after a decision silently created a fresh draft application."""
        self._activate()
        self._upload()
        submit_resp = self.client.post("/api/v1/me/application/submit")
        application_id = submit_resp.data["id"]

        self.client.force_authenticate(user=self.officer.user)
        self.client.post(f"/api/v1/admin/applications/{application_id}/claim")
        detail = self.client.get(f"/api/v1/admin/applications/{application_id}")
        slot_id = detail.data["submitted_documents"][0]["id"]
        self.client.post(
            f"/api/v1/admin/applications/{application_id}/documents/{slot_id}/review",
            {"verdict": "verified"},
            format="json",
        )
        self.client.post(
            f"/api/v1/admin/applications/{application_id}/approve", {"confirm": True}, format="json"
        )

        self.assertEqual(Application.objects.filter(scholarship=self.scholarship).count(), 1)

        self.client.force_authenticate(user=self._student_user())
        req_resp = self.client.get("/api/v1/me/requirements")
        self.assertEqual(str(req_resp.data["application_id"]), str(application_id))
        self.assertEqual(req_resp.data["application_status"], "approved")
        self.assertEqual(Application.objects.filter(scholarship=self.scholarship).count(), 1)

    def test_cannot_resubmit_an_approved_application(self):
        self._activate()
        self._upload()
        submit_resp = self.client.post("/api/v1/me/application/submit")
        application_id = submit_resp.data["id"]

        self.client.force_authenticate(user=self.officer.user)
        detail = self.client.get(f"/api/v1/admin/applications/{application_id}")
        slot_id = detail.data["submitted_documents"][0]["id"]
        self.client.post(
            f"/api/v1/admin/applications/{application_id}/documents/{slot_id}/review",
            {"verdict": "verified"},
            format="json",
        )
        self.client.post(f"/api/v1/admin/applications/{application_id}/approve", {"confirm": True}, format="json")

        student_user = self._student_user()
        self.client.force_authenticate(user=student_user)
        resubmit_resp = self.client.post("/api/v1/me/application/submit")
        self.assertEqual(resubmit_resp.status_code, 409)

    def test_student_can_reupload_a_rejected_document_while_application_stays_under_review(self):
        """
        A single document can be rejected by an officer mid-review without the
        whole application leaving under_review (that's a distinct, explicit
        "request information" action). The student must still be able to fix
        just that document without the application otherwise being editable.
        """
        self._activate()
        self._upload()
        submit_resp = self.client.post("/api/v1/me/application/submit")
        application_id = submit_resp.data["id"]

        self.client.force_authenticate(user=self.officer.user)
        detail = self.client.get(f"/api/v1/admin/applications/{application_id}")
        slot_id = detail.data["submitted_documents"][0]["id"]
        review_resp = self.client.post(
            f"/api/v1/admin/applications/{application_id}/documents/{slot_id}/review",
            {"verdict": "rejected", "comment": "Blurry scan"},
            format="json",
        )
        self.assertEqual(review_resp.status_code, 201, review_resp.content)

        # Application status is unaffected by a single-document rejection.
        detail = self.client.get(f"/api/v1/admin/applications/{application_id}")
        self.assertEqual(detail.data["status"], "under_review")

        self.client.force_authenticate(user=self._student_user())
        reupload = self._upload()
        self.assertEqual(reupload["status"], "pending")
        self.assertEqual(reupload["current_version"]["version_number"], 2)

    def test_student_can_delete_a_rejected_document_while_application_stays_under_review(self):
        self._activate()
        self._upload()
        submit_resp = self.client.post("/api/v1/me/application/submit")
        application_id = submit_resp.data["id"]

        self.client.force_authenticate(user=self.officer.user)
        detail = self.client.get(f"/api/v1/admin/applications/{application_id}")
        slot_id = detail.data["submitted_documents"][0]["id"]
        review_resp = self.client.post(
            f"/api/v1/admin/applications/{application_id}/documents/{slot_id}/review",
            {"verdict": "rejected", "comment": "Blurry scan"},
            format="json",
        )
        self.assertEqual(review_resp.status_code, 201, review_resp.content)

        self.client.force_authenticate(user=self._student_user())
        delete_resp = self.client.delete(f"/api/v1/me/documents/{slot_id}")
        self.assertEqual(delete_resp.status_code, 204, delete_resp.content)

    def test_request_additional_information_reopens_only_flagged_documents(self):
        self._activate()
        self._upload()
        submit_resp = self.client.post("/api/v1/me/application/submit")
        application_id = submit_resp.data["id"]
        student_user = self._student_user()

        self.client.force_authenticate(user=self.officer.user)
        detail = self.client.get(f"/api/v1/admin/applications/{application_id}")
        slot_id = detail.data["submitted_documents"][0]["id"]

        info_resp = self.client.post(
            f"/api/v1/admin/applications/{application_id}/request-information",
            {"submitted_document_ids": [slot_id], "comment": "Please redo."},
            format="json",
        )
        self.assertEqual(info_resp.status_code, 200)
        self.assertEqual(info_resp.data["status"], "additional_info_required")

        self.client.force_authenticate(user=student_user)
        req_resp = self.client.get("/api/v1/me/requirements")
        submitted = req_resp.data["requirements"][0]["submitted"]
        self.assertEqual(submitted["status"], "needs_clarification")

    def test_verification_officer_cannot_run_export(self):
        self.client.force_authenticate(user=self.officer.user)
        resp = self.client.get("/api/v1/admin/export")
        self.assertEqual(resp.status_code, 403)

    def test_document_download_requires_authorization(self):
        self._activate()
        submitted = self._upload()
        version_id = submitted["current_version"]["id"]

        self.client.logout()
        anon_resp = self.client.get(f"/api/v1/documents/{version_id}/download")
        self.assertIn(anon_resp.status_code, (401, 403))

    def test_activation_rejects_wrong_verification_code(self):
        self.client.post(
            "/api/v1/auth/activation/verify-identity",
            {"mat_number": "20260001", "utg_email": "student@utg.edu.gm"},
            format="json",
        )
        resp = self.client.post(
            "/api/v1/auth/activation/verify-code",
            {"mat_number": "20260001", "utg_email": "student@utg.edu.gm", "code": "000000"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_submission_blocked_when_mandatory_document_missing(self):
        self._activate()
        resp = self.client.post("/api/v1/me/application/submit")
        self.assertEqual(resp.status_code, 400)
