from django.db import models

from apps.core.models import TimeStampedModel


class Country(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    iso_code = models.CharField(max_length=3, unique=True)

    class Meta:
        db_table = "countries"
        ordering = ["name"]
        verbose_name_plural = "countries"

    def __str__(self):
        return self.name


class Institution(TimeStampedModel):
    name = models.CharField(max_length=200)
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="institutions")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "institutions"
        ordering = ["name"]
        unique_together = ("name", "country")

    def __str__(self):
        return f"{self.name} ({self.country.name})"


class ScholarshipType(TimeStampedModel):
    """
    Admin-configurable scholarship category (e.g. Undergraduate Merit,
    Graduate Research, Technical/Vocational). Kept as a lookup table rather
    than a fixed choices list because §13 of the specification scopes
    required-document rules by scholarship type, and a Ministry
    administrator must be able to add a new type without a code change.
    """

    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "scholarship_types"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Program(TimeStampedModel):
    class AcademicLevel(models.TextChoices):
        UNDERGRADUATE = "undergraduate", "Undergraduate"
        MASTERS = "masters", "Master's"
        DOCTORATE = "doctorate", "Doctorate"
        DIPLOMA = "diploma", "Diploma / Certificate"

    name = models.CharField(max_length=200)
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="programs")
    academic_level = models.CharField(max_length=20, choices=AcademicLevel.choices)

    class Meta:
        db_table = "programs"
        ordering = ["name"]
        unique_together = ("name", "institution", "academic_level")

    def __str__(self):
        return f"{self.name} — {self.institution.name}"
