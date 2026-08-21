from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel, UUIDPrimaryKeyModel


class Scholarship(UUIDPrimaryKeyModel, TimeStampedModel):
    """
    One awarded scholarship. A student may hold more than one over time
    (renewal, change of level), so this is not folded into Student —
    each is verified independently (system specification §9 ERD notes).
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        COMPLETED = "completed", "Completed"
        EXPIRED = "expired", "Expired"

    scholarship_reference_id = models.CharField(max_length=50, unique=True)
    student = models.ForeignKey(
        "accounts.Student",
        on_delete=models.PROTECT,
        related_name="scholarships",
        null=True,
        blank=True,
        help_text="Null until the Ministry-imported record behind this scholarship is activated (system specification §11).",
    )
    scholarship_type = models.ForeignKey(
        "catalog.ScholarshipType", on_delete=models.PROTECT, related_name="scholarships"
    )
    institution = models.ForeignKey("catalog.Institution", on_delete=models.PROTECT, related_name="scholarships")
    country = models.ForeignKey("catalog.Country", on_delete=models.PROTECT, related_name="scholarships")
    program = models.ForeignKey(
        "catalog.Program", on_delete=models.PROTECT, related_name="scholarships", null=True, blank=True
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ACTIVE)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        db_table = "scholarships"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.scholarship_reference_id} — {self.student.full_name}"

    @property
    def is_nearing_expiry(self):
        days_remaining = (self.end_date - timezone.now().date()).days
        return 0 <= days_remaining <= 60
