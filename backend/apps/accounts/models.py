from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import make_password
from django.db import models
from django.utils import timezone

from apps.core.fields import EncryptedCharField
from apps.core.models import TimeStampedModel, UUIDPrimaryKeyModel


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
    verification during activation (system specification §11, Option A+B):
    the student must match this record's scholarship ID + date of birth,
    plus a Ministry-issued one-time code, before a User/Student is created.
    """

    class ActivationChannel(models.TextChoices):
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"
        IN_PERSON = "in_person", "Issued in person / printed letter"

    scholarship_id = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=200)
    date_of_birth = models.DateField()
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    institution_name = models.CharField(max_length=200, blank=True)

    activation_code_hash = models.CharField(max_length=255)
    activation_code_channel = models.CharField(max_length=15, choices=ActivationChannel.choices)
    activation_code_expires_at = models.DateTimeField()
    activation_attempts = models.PositiveIntegerField(default=0)
    max_activation_attempts = models.PositiveIntegerField(default=5)

    activated_at = models.DateTimeField(null=True, blank=True)
    activated_student = models.OneToOneField(
        Student, on_delete=models.SET_NULL, null=True, blank=True, related_name="pre_registration"
    )
    imported_by = models.ForeignKey(Officer, on_delete=models.SET_NULL, null=True, related_name="imported_records")

    class Meta:
        db_table = "student_pre_registrations"

    def __str__(self):
        return f"{self.scholarship_id} — {self.full_name}"

    @property
    def is_activated(self):
        return self.activated_at is not None

    @property
    def is_code_expired(self):
        return timezone.now() >= self.activation_code_expires_at

    @property
    def is_locked_out(self):
        return self.activation_attempts >= self.max_activation_attempts

    def set_activation_code(self, raw_code):
        self.activation_code_hash = make_password(raw_code)


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
