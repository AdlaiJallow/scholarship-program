from django.conf import settings
from django.db import models

from apps.core.models import UUIDPrimaryKeyModel


class AuditLog(UUIDPrimaryKeyModel):
    """
    Append-only record of every security-relevant action (system
    specification §15). Immutability is enforced at the database grant
    level in production (see infra/sql/audit_immutability.sql) — the
    application-layer save()/delete() guards below are a second line of
    defense, not the primary control, because a control that only lives in
    application code is bypassed by direct database access.
    """

    class Action(models.TextChoices):
        LOGIN_SUCCESS = "login.success", "Login succeeded"
        LOGIN_FAILURE = "login.failure", "Login failed"
        LOGOUT = "logout", "Logout"
        ACCOUNT_ACTIVATED = "account.activated", "Account activated"
        PASSWORD_RESET_REQUESTED = "password.reset_requested", "Password reset requested"
        PASSWORD_RESET_COMPLETED = "password.reset_completed", "Password reset completed"
        DOCUMENT_UPLOADED = "document.uploaded", "Document uploaded"
        DOCUMENT_DELETED = "document.deleted", "Document deleted"
        DOCUMENT_VIEWED = "document.viewed", "Document viewed"
        DOCUMENT_REVIEWED = "document.reviewed", "Document reviewed"
        APPLICATION_SUBMITTED = "application.submitted", "Application submitted"
        APPLICATION_VIEWED = "application.viewed", "Application viewed"
        APPLICATION_APPROVED = "application.approved", "Application approved"
        APPLICATION_REJECTED = "application.rejected", "Application rejected"
        APPLICATION_INFO_REQUESTED = "application.info_requested", "Additional information requested"
        APPLICATION_REASSIGNED = "application.reassigned", "Application reassigned"
        APPLICATION_RESUBMITTED = "application.resubmitted", "Application resubmitted"
        EXPORT_GENERATED = "export.generated", "Export generated"
        REQUIREMENT_CONFIGURED = "requirement.configured", "Document requirement configured"
        ROLE_PERMISSION_CHANGED = "role.permission_changed", "Role/permission changed"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs"
    )
    actor_email_snapshot = models.EmailField(blank=True)
    action = models.CharField(max_length=50, choices=Action.choices)
    target_type = models.CharField(max_length=50, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["target_type", "target_id"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} by {self.actor_email_snapshot or 'system'} at {self.created_at}"

    def save(self, *args, **kwargs):
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise PermissionError("Audit log entries are immutable and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Audit log entries cannot be deleted through the application.")
