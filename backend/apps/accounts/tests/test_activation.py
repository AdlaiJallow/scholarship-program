"""
Coverage of the MAT number + UTG email self-activation flow: identity
verification, emailed one-time codes, resend behavior, and account
creation. See apps.verification.tests.test_workflow for the end-to-end
happy path exercised as part of the document-upload workflow.
"""

import re
from datetime import date, timedelta

from django.core import mail
from django.core.cache import cache
from django.db import IntegrityError
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import EmailVerificationCode, StudentPreRegistration
from apps.audit.models import AuditLog

MAT_NUMBER = "20260001"
UTG_EMAIL = "student@utg.edu.gm"


class ActivationTests(APITestCase):
    def setUp(self):
        # ScopedRateThrottle state lives in the cache, not the DB, so it
        # isn't reset by the per-test transaction rollback — clear it
        # explicitly or throttle counts leak between tests in this class.
        cache.clear()
        self.pre_reg = StudentPreRegistration.objects.create(
            mat_number=MAT_NUMBER,
            full_name="Test Student",
            date_of_birth=date(2002, 1, 1),
            email=UTG_EMAIL,
        )

    def _verify_identity(self, mat_number=MAT_NUMBER, utg_email=UTG_EMAIL):
        return self.client.post(
            "/api/v1/auth/activation/verify-identity",
            {"mat_number": mat_number, "utg_email": utg_email},
            format="json",
        )

    def _latest_code(self):
        return re.search(r"code is: (\d+)", mail.outbox[-1].body).group(1)

    def _verify_code(self, code, mat_number=MAT_NUMBER, utg_email=UTG_EMAIL):
        return self.client.post(
            "/api/v1/auth/activation/verify-code",
            {"mat_number": mat_number, "utg_email": utg_email, "code": code},
            format="json",
        )

    def _create_account(self, token, password="SuperSecret123!", **extra):
        payload = {"verification_token": token, "password": password, **extra}
        return self.client.post("/api/v1/auth/activation/create-account", payload, format="json")

    def test_happy_path(self):
        resp = self._verify_identity()
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(len(mail.outbox), 1)

        code = self._latest_code()
        resp = self._verify_code(code)
        self.assertEqual(resp.status_code, 200, resp.content)
        token = resp.json()["verification_token"]

        resp = self._create_account(token, phone_number="+220 700 0002", address="Banjul", gender="female")
        self.assertEqual(resp.status_code, 201, resp.content)

        me = self.client.get("/api/v1/me/profile")
        self.assertEqual(me.status_code, 200)

        self.pre_reg.refresh_from_db()
        self.assertTrue(self.pre_reg.is_activated)
        self.assertIsNotNone(self.pre_reg.activated_student)
        self.assertIsNotNone(self.pre_reg.activated_student.user.email_verified_at)

        actions = list(AuditLog.objects.values_list("action", flat=True))
        self.assertIn(AuditLog.Action.VERIFICATION_CODE_SENT, actions)
        self.assertIn(AuditLog.Action.VERIFICATION_CODE_VERIFIED, actions)
        self.assertIn(AuditLog.Action.ACCOUNT_ACTIVATED, actions)

    def test_unknown_mat_number_gives_generic_message(self):
        resp = self._verify_identity(mat_number="99999999")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(
            AuditLog.objects.filter(action=AuditLog.Action.IDENTITY_VERIFICATION_FAILED).exists()
        )
        return resp.json()["detail"]

    def test_mismatched_email_gives_same_generic_message_as_unknown_mat(self):
        mismatch_detail = self._verify_identity(utg_email="someoneelse@utg.edu.gm").json()["detail"]
        unknown_detail = self.test_unknown_mat_number_gives_generic_message()
        self.assertEqual(mismatch_detail, unknown_detail)

    def test_already_activated_blocks_with_distinct_message(self):
        self.pre_reg.activated_at = timezone.now()
        self.pre_reg.save(update_fields=["activated_at"])

        resp = self._verify_identity()
        self.assertEqual(resp.status_code, 409)
        self.assertTrue(resp.json()["already_activated"])
        self.assertTrue(
            AuditLog.objects.filter(action=AuditLog.Action.ACTIVATION_DUPLICATE_BLOCKED).exists()
        )

    def test_expired_code_is_rejected(self):
        self._verify_identity()
        code = EmailVerificationCode.objects.get(pre_registration=self.pre_reg)
        code.expires_at = timezone.now() - timedelta(seconds=1)
        code.save(update_fields=["expires_at"])

        resp = self._verify_code(self._latest_code())
        self.assertEqual(resp.status_code, 400)

    def test_wrong_code_attempts_exceeding_limit_locks_out(self):
        self._verify_identity()
        correct_code = self._latest_code()

        for _ in range(4):
            resp = self._verify_code("000000")
            self.assertEqual(resp.status_code, 400)

        resp = self._verify_code("000000")
        self.assertEqual(resp.status_code, 429)

        # Even the correct code is now locked out until a resend.
        resp = self._verify_code(correct_code)
        self.assertEqual(resp.status_code, 429)

    def test_resend_cooldown_blocks_immediate_repeat(self):
        self._verify_identity()
        resp = self.client.post(
            "/api/v1/auth/activation/resend-code",
            {"mat_number": MAT_NUMBER, "utg_email": UTG_EMAIL},
            format="json",
        )
        self.assertEqual(resp.status_code, 429)
        self.assertIn("retry_after_seconds", resp.json())

    @override_settings(ACTIVATION_RESEND_COOLDOWN_SECONDS=0)
    def test_resend_invalidates_previous_code(self):
        self._verify_identity()
        old_code = self._latest_code()

        resp = self.client.post(
            "/api/v1/auth/activation/resend-code",
            {"mat_number": MAT_NUMBER, "utg_email": UTG_EMAIL},
            format="json",
        )
        self.assertEqual(resp.status_code, 202, resp.content)
        new_code = self._latest_code()
        self.assertNotEqual(old_code, new_code)

        self.assertEqual(self._verify_code(old_code).status_code, 400)
        self.assertEqual(self._verify_code(new_code).status_code, 200)

    @override_settings(ACTIVATION_RESEND_COOLDOWN_SECONDS=0, ACTIVATION_MAX_RESENDS_PER_DAY=2)
    def test_resend_rolling_window_limit(self):
        self._verify_identity()  # 1st code
        self.client.post(
            "/api/v1/auth/activation/resend-code",
            {"mat_number": MAT_NUMBER, "utg_email": UTG_EMAIL},
            format="json",
        )  # 2nd code — hits the limit of 2

        resp = self.client.post(
            "/api/v1/auth/activation/resend-code",
            {"mat_number": MAT_NUMBER, "utg_email": UTG_EMAIL},
            format="json",
        )
        self.assertEqual(resp.status_code, 429)

    def test_duplicate_mat_number_rejected_at_ministry_import(self):
        with self.assertRaises(IntegrityError):
            StudentPreRegistration.objects.create(
                mat_number=MAT_NUMBER,
                full_name="Someone Else",
                date_of_birth=date(2003, 1, 1),
                email="other@utg.edu.gm",
            )

    def test_weak_password_rejected(self):
        self._verify_identity()
        token = self._verify_code(self._latest_code()).json()["verification_token"]
        resp = self._create_account(token, password="short")
        self.assertEqual(resp.status_code, 400)

    @override_settings(ACTIVATION_TOKEN_TTL_SECONDS=-1)
    def test_expired_verification_token_rejected(self):
        self._verify_identity()
        token = self._verify_code(self._latest_code()).json()["verification_token"]
        resp = self._create_account(token)
        self.assertEqual(resp.status_code, 400)

    def test_activation_endpoints_do_not_require_csrf(self):
        self.client.handler.enforce_csrf_checks = True
        try:
            resp = self._verify_identity()
            self.assertEqual(resp.status_code, 200, resp.content)
            code = self._latest_code()
            resp = self._verify_code(code)
            self.assertEqual(resp.status_code, 200, resp.content)
            token = resp.json()["verification_token"]
            resp = self._create_account(token)
            self.assertEqual(resp.status_code, 201, resp.content)
        finally:
            self.client.handler.enforce_csrf_checks = False
