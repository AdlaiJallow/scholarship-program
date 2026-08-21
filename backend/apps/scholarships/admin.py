from django.contrib import admin

from .models import Scholarship


@admin.register(Scholarship)
class ScholarshipAdmin(admin.ModelAdmin):
    list_display = (
        "scholarship_reference_id",
        "student",
        "scholarship_type",
        "institution",
        "country",
        "status",
        "end_date",
    )
    list_filter = ("status", "scholarship_type", "institution", "country")
    search_fields = ("scholarship_reference_id", "student__full_name")
    autocomplete_fields = ("student", "institution", "country", "program")
