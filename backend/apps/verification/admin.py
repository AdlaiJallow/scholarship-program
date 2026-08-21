from django.contrib import admin

from .models import (
    Application,
    ApplicationStatusHistory,
    DocumentReview,
    DocumentVersion,
    RequiredDocument,
    SubmittedDocument,
)


@admin.register(RequiredDocument)
class RequiredDocumentAdmin(admin.ModelAdmin):
    list_display = ("name", "scholarship_type", "institution", "country", "is_mandatory", "is_active")
    list_filter = ("is_mandatory", "is_active", "renewal_policy")
    search_fields = ("name",)


class SubmittedDocumentInline(admin.TabularInline):
    model = SubmittedDocument
    extra = 0
    readonly_fields = ("required_document", "status", "current_version")
    can_delete = False


class ApplicationStatusHistoryInline(admin.TabularInline):
    model = ApplicationStatusHistory
    extra = 0
    readonly_fields = ("from_status", "to_status", "changed_by", "note", "created_at")
    can_delete = False
    ordering = ("created_at",)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("reference_number", "scholarship", "status", "assigned_officer", "submitted_at")
    list_filter = ("status",)
    search_fields = ("reference_number", "scholarship__scholarship_reference_id", "scholarship__student__full_name")
    inlines = [SubmittedDocumentInline, ApplicationStatusHistoryInline]
    readonly_fields = ("reference_number", "submitted_at", "decided_at", "decided_by")


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ("submitted_document", "version_number", "scan_status", "uploaded_at")
    list_filter = ("scan_status",)
    readonly_fields = [f.name for f in DocumentVersion._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DocumentReview)
class DocumentReviewAdmin(admin.ModelAdmin):
    list_display = ("document_version", "officer", "verdict", "created_at")
    list_filter = ("verdict",)
