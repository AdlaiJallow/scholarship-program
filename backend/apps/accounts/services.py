"""
Activation and login-security logic (system specification §11, §16).
Identity verification uses the Option A + B hybrid recommended in the
specification: a Ministry-imported record (A) plus a one-time activation
code delivered by whatever channel currently reaches the student (B) —
never open self-registration, and never unattended fuzzy name/DOB matching.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services import log_action

from .models import FailedLoginAttempt, Student, StudentPreRegistration, User


class ActivationError(Exception):
    pass


def is_locked_out(email, ip_address):
    window_start = timezone.now() - timedelta(minutes=settings.ACCOUNT_LOCKOUT_WINDOW_MINUTES)
    recent_failures = FailedLoginAttempt.objects.filter(email__iexact=email, attempted_at__gte=window_start).count()
    return recent_failures >= settings.ACCOUNT_LOCKOUT_THRESHOLD


def record_failed_login(email, ip_address, request=None):
    FailedLoginAttempt.objects.create(email=email, ip_address=ip_address or "0.0.0.0")
    log_action(AuditLog.Action.LOGIN_FAILURE, metadata={"email": email}, request=request)


def record_successful_login(user, request=None):
    log_action(AuditLog.Action.LOGIN_SUCCESS, actor=user, request=request)


def activate_student_account(scholarship_id, date_of_birth, verification_code, password, request=None):
    try:
        pre_reg = StudentPreRegistration.objects.get(scholarship_id=scholarship_id)
    except StudentPreRegistration.DoesNotExist as exc:
        raise ActivationError("We could not find a scholarship record matching those details.") from exc

    if pre_reg.is_activated:
        raise ActivationError("This scholarship record has already been activated. Try signing in instead.")
    if pre_reg.is_locked_out:
        raise ActivationError("Too many failed activation attempts. Please contact the Ministry to reissue a code.")
    if pre_reg.is_code_expired:
        raise ActivationError("This activation code has expired. Please contact the Ministry to reissue a code.")
    if pre_reg.date_of_birth != date_of_birth:
        pre_reg.activation_attempts += 1
        pre_reg.save(update_fields=["activation_attempts"])
        raise ActivationError("We could not find a scholarship record matching those details.")
    if not check_password(verification_code, pre_reg.activation_code_hash):
        pre_reg.activation_attempts += 1
        pre_reg.save(update_fields=["activation_attempts"])
        raise ActivationError("We could not find a scholarship record matching those details.")

    if not pre_reg.email:
        raise ActivationError("No email is on file for this record. Please contact the Ministry.")

    user = User.objects.create_user(
        email=pre_reg.email,
        password=password,
        user_type=User.UserType.STUDENT,
        is_active=True,
        email_verified_at=timezone.now(),
    )
    student = Student.objects.create(
        user=user,
        full_name=pre_reg.full_name,
        date_of_birth=pre_reg.date_of_birth,
        phone_number=pre_reg.phone_number,
        national_id_number="",
    )
    pre_reg.activated_at = timezone.now()
    pre_reg.activated_student = student
    pre_reg.save(update_fields=["activated_at", "activated_student"])

    # Link any Ministry-imported Scholarship record(s) that were created
    # under this scholarship ID before the student ever activated an
    # account (system specification §11: pre-registration precedes login).
    from apps.scholarships.models import Scholarship

    Scholarship.objects.filter(scholarship_reference_id=pre_reg.scholarship_id, student__isnull=True).update(
        student=student
    )

    log_action(AuditLog.Action.ACCOUNT_ACTIVATED, actor=user, target=student, request=request)
    return user
