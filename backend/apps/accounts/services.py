"""
Activation and login-security logic. Identity verification for
self-activation is MAT number + UTG email against a Ministry-imported
StudentPreRegistration record, followed by a system-generated one-time code
emailed to that address — never open self-registration, and never reveal
which submitted field (if any) didn't match a real record.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services import log_action

from .models import EmailVerificationCode, FailedLoginAttempt, Student, StudentPreRegistration, User

GENERIC_MISMATCH_MESSAGE = "We could not verify your details. Please check your MAT number and UTG email address and try again."
ALREADY_ACTIVATED_MESSAGE = "This account has already been activated. Please sign in, or use password recovery if you've forgotten your password."
GENERIC_CODE_ERROR_MESSAGE = "That code is incorrect or has expired. Please check it and try again, or request a new one."

VERIFICATION_TOKEN_SALT = "accounts.identity-verified"


class IdentityMismatchError(Exception):
    pass


class AlreadyActivatedError(Exception):
    pass


class CodeVerificationError(Exception):
    pass


class CodeLockedOutError(Exception):
    pass


class ResendCooldownError(Exception):
    def __init__(self, retry_after_seconds):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Please wait {retry_after_seconds}s before requesting another code.")


class ResendLimitExceededError(Exception):
    pass


class VerificationTokenError(Exception):
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


def _generate_raw_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def _match_pre_registration(mat_number, utg_email, request=None):
    """
    Shared lookup for verify_identity/verify_code/resend: finds the
    Ministry record and checks it hasn't already been activated, raising the
    same generic mismatch error whether the MAT number doesn't exist or the
    email doesn't match it — never reveal which one was wrong.
    """
    try:
        pre_reg = StudentPreRegistration.objects.get(mat_number=mat_number)
    except StudentPreRegistration.DoesNotExist:
        log_action(
            AuditLog.Action.IDENTITY_VERIFICATION_FAILED, request=request, metadata={"mat_number": mat_number}
        )
        raise IdentityMismatchError(GENERIC_MISMATCH_MESSAGE)

    if pre_reg.is_activated:
        log_action(AuditLog.Action.ACTIVATION_DUPLICATE_BLOCKED, target=pre_reg, request=request)
        raise AlreadyActivatedError(ALREADY_ACTIVATED_MESSAGE)

    if pre_reg.email.lower() != utg_email.lower():
        log_action(
            AuditLog.Action.IDENTITY_VERIFICATION_FAILED,
            target=pre_reg,
            request=request,
            metadata={"mat_number": mat_number},
        )
        raise IdentityMismatchError(GENERIC_MISMATCH_MESSAGE)

    return pre_reg


def send_verification_code(pre_reg, request=None, is_resend=False):
    """
    Invalidates any currently-active code for this pre-registration, creates
    a fresh one, and emails it. Wrapped in a transaction so a failed send
    doesn't leave an uncounted code toward the resend rolling window.
    """
    from .emails import send_activation_code_email

    with transaction.atomic():
        EmailVerificationCode.objects.filter(
            pre_registration=pre_reg, used_at__isnull=True, invalidated_at__isnull=True
        ).update(invalidated_at=timezone.now())

        raw_code = _generate_raw_code()
        code = EmailVerificationCode(
            pre_registration=pre_reg,
            email=pre_reg.email,
            expires_at=timezone.now() + timedelta(hours=settings.ACTIVATION_CODE_EXPIRY_HOURS),
            max_attempts=settings.ACTIVATION_MAX_CODE_ATTEMPTS,
            requested_ip=getattr(request, "audit_ip", None),
        )
        code.set_code(raw_code)
        code.save()
        send_activation_code_email(pre_reg, raw_code, is_resend=is_resend)

    log_action(
        AuditLog.Action.VERIFICATION_CODE_RESENT if is_resend else AuditLog.Action.VERIFICATION_CODE_SENT,
        target=pre_reg,
        request=request,
        metadata={"email_verification_code_id": str(code.id)},
    )
    return code


def verify_identity(mat_number, utg_email, request=None):
    pre_reg = _match_pre_registration(mat_number, utg_email, request=request)
    send_verification_code(pre_reg, request=request, is_resend=False)
    return pre_reg


def resend_verification_code(mat_number, utg_email, request=None):
    pre_reg = _match_pre_registration(mat_number, utg_email, request=request)

    window_start = timezone.now() - timedelta(hours=24)
    recent_count = EmailVerificationCode.objects.filter(
        pre_registration=pre_reg, created_at__gte=window_start
    ).count()
    if recent_count >= settings.ACTIVATION_MAX_RESENDS_PER_DAY:
        raise ResendLimitExceededError(
            "You've reached the maximum number of codes you can request today. Please try again later."
        )

    last_code = EmailVerificationCode.objects.filter(pre_registration=pre_reg).order_by("-created_at").first()
    if last_code is not None:
        elapsed = (timezone.now() - last_code.created_at).total_seconds()
        cooldown = settings.ACTIVATION_RESEND_COOLDOWN_SECONDS
        if elapsed < cooldown:
            raise ResendCooldownError(retry_after_seconds=int(cooldown - elapsed))

    return send_verification_code(pre_reg, request=request, is_resend=True)


def verify_code(mat_number, utg_email, code, request=None):
    pre_reg = _match_pre_registration(mat_number, utg_email, request=request)

    verification_code = (
        EmailVerificationCode.objects.filter(
            pre_registration=pre_reg, used_at__isnull=True, invalidated_at__isnull=True
        )
        .order_by("-created_at")
        .first()
    )
    if verification_code is None or verification_code.is_expired:
        log_action(AuditLog.Action.VERIFICATION_CODE_FAILED, target=pre_reg, request=request)
        raise CodeVerificationError(GENERIC_CODE_ERROR_MESSAGE)

    if verification_code.is_locked_out:
        log_action(AuditLog.Action.VERIFICATION_CODE_FAILED, target=pre_reg, request=request)
        raise CodeLockedOutError("Too many incorrect attempts. Please request a new code.")

    if not verification_code.check_code(code):
        verification_code.attempts += 1
        verification_code.save(update_fields=["attempts"])
        log_action(
            AuditLog.Action.VERIFICATION_CODE_FAILED,
            target=pre_reg,
            request=request,
            metadata={"attempts": verification_code.attempts},
        )
        if verification_code.is_locked_out:
            raise CodeLockedOutError("Too many incorrect attempts. Please request a new code.")
        raise CodeVerificationError(GENERIC_CODE_ERROR_MESSAGE)

    verification_code.used_at = timezone.now()
    verification_code.save(update_fields=["used_at"])
    log_action(AuditLog.Action.VERIFICATION_CODE_VERIFIED, target=pre_reg, request=request)

    return signing.dumps(
        {"pre_registration_id": str(pre_reg.id), "email_verification_code_id": str(verification_code.id)},
        salt=VERIFICATION_TOKEN_SALT,
    )


def create_student_account(verification_token, password, phone_number="", address="", gender="", request=None):
    try:
        payload = signing.loads(
            verification_token, salt=VERIFICATION_TOKEN_SALT, max_age=settings.ACTIVATION_TOKEN_TTL_SECONDS
        )
    except signing.BadSignature:
        raise VerificationTokenError("Your verification session has expired. Please verify your code again.")

    pre_reg = StudentPreRegistration.objects.filter(id=payload["pre_registration_id"]).first()
    if pre_reg is None:
        raise VerificationTokenError("Your verification session is no longer valid. Please start again.")
    if pre_reg.is_activated:
        raise AlreadyActivatedError(ALREADY_ACTIVATED_MESSAGE)

    code = EmailVerificationCode.objects.filter(
        id=payload["email_verification_code_id"], pre_registration=pre_reg
    ).first()
    if code is None or not code.is_used:
        raise VerificationTokenError("Your verification session is no longer valid. Please start again.")

    if User.objects.filter(email__iexact=pre_reg.email).exists():
        raise AlreadyActivatedError(ALREADY_ACTIVATED_MESSAGE)

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
        phone_number=phone_number or pre_reg.phone_number,
        address=address,
        gender=gender or Student.Gender.UNSPECIFIED,
        national_id_number="",
    )
    pre_reg.activated_at = timezone.now()
    pre_reg.activated_student = student
    pre_reg.save(update_fields=["activated_at", "activated_student"])

    # Link any Ministry-imported Scholarship record(s) that were created
    # under this MAT number before the student ever activated an account.
    from apps.scholarships.models import Scholarship

    Scholarship.objects.filter(scholarship_reference_id=pre_reg.mat_number, student__isnull=True).update(
        student=student
    )

    log_action(AuditLog.Action.ACCOUNT_ACTIVATED, actor=user, target=student, request=request)
    return user
