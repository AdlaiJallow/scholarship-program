from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import check_password, make_password
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from apps.core.fields import EncryptedCharField
from apps.core.models import TimeStampedModel, UUIDPrimaryKeyModel

mat_number_validator = RegexValidator(r"^\d{8}$", "MAT number must be exactly 8 digits.")


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("user_type", User.UserType.OFFICER)
        extra_fields.setdefault("is_active", True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, UUIDPrimaryKeyModel, TimeStampedModel):
    """
    Shared identity for both scholarship holders and Ministry staff — one
    auth model, discriminated by user_type, per the ERD note in the system
    specification §9: avoids duplicating login/session/password-reset logic
    for what is otherwise the same authentication concern.
    """

    class UserType(models.TextChoices):
        STUDENT = "student", "Student"
        OFFICER = "officer", "Ministry officer"

    email = models.EmailField(unique=True)
    user_type = models.CharField(max_length=10, choices=UserType.choices)
    is_active = models.BooleanField(default=False)  # False until activation completes
    is_staff = models.BooleanField(default=False)  # Django admin access only
    is_superuser = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    must_change_password = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser


class Role(TimeStampedModel):
    """RBAC role, e.g. Super Administrator, Verification Officer, Supervisor, Read-Only/Reporting Officer."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_system_role = models.BooleanField(
        default=False, help_text="System roles (seeded via migration) cannot be deleted from the admin UI."
    )

    class Meta:
        db_table = "roles"

    def __str__(self):
        return self.name


class Permission(TimeStampedModel):
    """A single grantable capability, e.g. 'applications.approve', 'exports.run'."""

    codename = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255)
    roles = models.ManyToManyField(Role, related_name="permissions", blank=True)

    class Meta:
        db_table = "permissions"

    def __str__(self):
        return self.codename


class Officer(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="officer_profile")
    full_name = models.CharField(max_length=200)
    employee_id = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=150, blank=True)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="officers")
    supervisor = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="supervisees"
    )
    is_on_leave = models.BooleanField(default=False)

    class Meta:
        db_table = "officers"

    def __str__(self):
        return f"{self.full_name} ({self.role.name})"


class Student(TimeStampedModel):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"
        UNSPECIFIED = "unspecified", "Prefer not to say"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    full_name = models.CharField(max_length=200)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=15, choices=Gender.choices, default=Gender.UNSPECIFIED)
    national_id_number = EncryptedCharField(max_cleartext_length=64)
    phone_number = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)

    class Meta:
        db_table = "students"

    def __str__(self):
        return self.full_name


class StudentPreRegistration(TimeStampedModel):
    """
    A Ministry-imported scholarship-holder record that has not yet been
    claimed by a student account. This is the source of truth for identity
    verification during activation: the student must submit a MAT number
    and UTG email address matching this record before the system will
    email a one-time verification code (see EmailVerificationCode) and let
    them create a User/Student account.
    """

    mat_number = models.CharField(max_length=8, unique=True, validators=[mat_number_validator])
    full_name = models.CharField(max_length=200)
    date_of_birth = models.DateField()
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    institution_name = models.CharField(max_length=200, blank=True)

    activated_at = models.DateTimeField(null=True, blank=True)
    activated_student = models.OneToOneField(
        Student, on_delete=models.SET_NULL, null=True, blank=True, related_name="pre_registration"
    )
    imported_by = models.ForeignKey(Officer, on_delete=models.SET_NULL, null=True, related_name="imported_records")

    class Meta:
        db_table = "student_pre_registrations"

    def __str__(self):
        return f"{self.mat_number} — {self.full_name}"

    @property
    def is_activated(self):
        return self.activated_at is not None


class EmailVerificationCode(TimeStampedModel, UUIDPrimaryKeyModel):
    """
    A one-time code emailed to a student's UTG address to prove they control
    it, as part of the self-activation flow. Kept as its own model (rather
    than fields on StudentPreRegistration) so a resend can invalidate the
    previous code while preserving both for the audit trail, and so
    expiry/attempt-lockout are scoped per code, not per pre-registration.
    """

    pre_registration = models.ForeignKey(
        StudentPreRegistration, on_delete=models.CASCADE, related_name="verification_codes"
    )
    email = models.EmailField()
    code_hash = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=5)
    used_at = models.DateTimeField(null=True, blank=True)
    invalidated_at = models.DateTimeField(null=True, blank=True)
    requested_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "email_verification_codes"
        indexes = [models.Index(fields=["pre_registration", "created_at"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"code for {self.pre_registration.mat_number} sent {self.created_at}"

    def set_code(self, raw_code):
        self.code_hash = make_password(raw_code)

    def check_code(self, raw_code):
        return check_password(raw_code, self.code_hash)

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_invalidated(self):
        return self.invalidated_at is not None

    @property
    def is_locked_out(self):
        return self.attempts >= self.max_attempts

    @property
    def is_valid(self):
        return not (self.is_expired or self.is_used or self.is_invalidated or self.is_locked_out)


class FailedLoginAttempt(models.Model):
    """
    Brute-force / lockout tracking (system specification §16). Kept
    separate from AuditLogs (apps.audit) because this is short-lived
    operational state that gets pruned, not a permanent record.
    """

    email = models.EmailField(db_index=True)
    ip_address = models.GenericIPAddressField()
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "failed_login_attempts"
        indexes = [models.Index(fields=["email", "attempted_at"])]
