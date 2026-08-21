from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel, UUIDPrimaryKeyModel


class RequiredDocument(TimeStampedModel):
    """
    Admin-configured document requirement (system specification §13). Never
    hard-code a document list in code — a null scope field means "applies
    to every scholarship in that dimension", so a rule can be as broad as
    "every scholarship holder needs a passport photo" or as narrow as
    "Fulbright recipients at University of The Gambia need form X".
    """

    class RenewalPolicy(models.TextChoices):
        ONE_TIME = "one_time", "Submitted once, never expires"
        PER_ACADEMIC_YEAR = "per_academic_year", "Must be renewed every academic year"
        FIXED_VALIDITY_DAYS = "fixed_validity_days", "Expires N days after issue"

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    scholarship_type = models.ForeignKey(
        "catalog.ScholarshipType", on_delete=models.CASCADE, null=True, blank=True, related_name="required_documents"
    )
    institution = models.ForeignKey(
        "catalog.Institution", on_delete=models.CASCADE, null=True, blank=True, related_name="required_documents"
    )
    country = models.ForeignKey(
        "catalog.Country", on_delete=models.CASCADE, null=True, blank=True, related_name="required_documents"
    )

    is_mandatory = models.BooleanField(default=True)
    accepted_file_types = models.JSONField(default=list, help_text='e.g. ["pdf", "jpg", "jpeg", "png"]')
    max_file_size_bytes = models.PositiveIntegerField(default=5 * 1024 * 1024)

    renewal_policy = models.CharField(max_length=20, choices=RenewalPolicy.choices, default=RenewalPolicy.ONE_TIME)
    validity_days = models.PositiveIntegerField(
        null=True, blank=True, help_text="Only used when renewal_policy = fixed_validity_days"
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "required_documents"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @classmethod
    def resolve_for_scholarship(cls, scholarship):
        return cls.objects.filter(is_active=True).filter(
            Q(scholarship_type__isnull=True) | Q(scholarship_type=scholarship.scholarship_type),
            Q(institution__isnull=True) | Q(institution=scholarship.institution),
            Q(country__isnull=True) | Q(country=scholarship.country),
        )


OPEN_APPLICATION_STATUSES = [
    "in_progress",
    "submitted",
    "under_review",
    "additional_info_required",
    "resubmission_required",
]


class Application(UUIDPrimaryKeyModel, TimeStampedModel):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        ADDITIONAL_INFO_REQUIRED = "additional_info_required", "Additional Information Required"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        RESUBMISSION_REQUIRED = "resubmission_required", "Resubmission Required"

    class RejectionReason(models.TextChoices):
        INVALID_DOCUMENT = "invalid_document", "Invalid document"
        EXPIRED_DOCUMENT = "expired_document", "Expired document"
        MISSING_DOCUMENT = "missing_document", "Missing document"
        INFORMATION_MISMATCH = "information_mismatch", "Information mismatch"
        UNCLEAR_DOCUMENT = "unclear_document", "Unclear document"
        INFO_CORRECTION_NEEDED = "info_correction_needed", "Student information requires correction"
        OTHER = "other", "Other"

    reference_number = models.CharField(max_length=30, unique=True, blank=True)
    scholarship = models.ForeignKey(
        "scholarships.Scholarship", on_delete=models.PROTECT, related_name="applications"
    )
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.NOT_STARTED)

    assigned_officer = models.ForeignKey(
        "accounts.Officer", on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_applications"
    )

    declaration_confirmed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        "accounts.Officer", on_delete=models.SET_NULL, null=True, blank=True, related_name="decided_applications"
    )
    decision_remarks = models.TextField(blank=True)
    rejection_reason = models.CharField(max_length=30, choices=RejectionReason.choices, blank=True)
    rejection_detail = models.TextField(blank=True)

    class Meta:
        db_table = "applications"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["scholarship"],
                condition=Q(status__in=OPEN_APPLICATION_STATUSES),
                name="one_open_application_per_scholarship",
            )
        ]

    def __str__(self):
        return self.reference_number or f"Application {self.id}"

    @property
    def is_editable_by_student(self):
        return self.status in {
            self.Status.NOT_STARTED,
            self.Status.IN_PROGRESS,
            self.Status.ADDITIONAL_INFO_REQUIRED,
            self.Status.RESUBMISSION_REQUIRED,
        }


class SubmittedDocument(TimeStampedModel):
    """
    One checklist "slot" for an application — the current review status of
    a requirement, whose actual file content lives in ordered, immutable
    DocumentVersion rows (never overwritten, per §13/§22).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"
        NEEDS_CLARIFICATION = "needs_clarification", "Needs clarification"

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="submitted_documents")
    required_document = models.ForeignKey(
        RequiredDocument, on_delete=models.PROTECT, related_name="submitted_documents"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    current_version = models.ForeignKey(
        "DocumentVersion", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        db_table = "submitted_documents"
        unique_together = ("application", "required_document")

    def __str__(self):
        return f"{self.required_document.name} for {self.application}"


class DocumentVersion(UUIDPrimaryKeyModel):
    """Immutable — a correction always creates a new row, never edits this one (system specification §13)."""

    class ScanStatus(models.TextChoices):
        PENDING = "pending", "Scan pending"
        CLEAN = "clean", "Clean"
        INFECTED = "infected", "Infected — quarantined"
        ERROR = "error", "Scan error"

    submitted_document = models.ForeignKey(SubmittedDocument, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    storage_key = models.CharField(max_length=500)
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    file_size_bytes = models.PositiveIntegerField()
    checksum_sha256 = models.CharField(max_length=64)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    scan_status = models.CharField(max_length=15, choices=ScanStatus.choices, default=ScanStatus.PENDING)
    scan_completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "document_versions"
        unique_together = ("submitted_document", "version_number")
        ordering = ["submitted_document", "version_number"]

    def __str__(self):
        return f"{self.submitted_document.required_document.name} v{self.version_number}"


class DocumentReview(UUIDPrimaryKeyModel):
    """An officer's decision on one specific document version — reviews always reference the version acted on, not just the slot (system specification §9)."""

    class Verdict(models.TextChoices):
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"
        NEEDS_CLARIFICATION = "needs_clarification", "Needs clarification"

    document_version = models.ForeignKey(DocumentVersion, on_delete=models.CASCADE, related_name="reviews")
    officer = models.ForeignKey("accounts.Officer", on_delete=models.PROTECT, related_name="document_reviews")
    verdict = models.CharField(max_length=20, choices=Verdict.choices)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "document_reviews"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.verdict} — {self.document_version}"


class ApplicationStatusHistory(UUIDPrimaryKeyModel):
    """Append-only status trail. The dashboard's 'last update' reads the latest row here, never a mutable field (system specification §9)."""

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=30, blank=True)
    to_status = models.CharField(max_length=30)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "application_status_history"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.application_id}: {self.from_status} -> {self.to_status}"
