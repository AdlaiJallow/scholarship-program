from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel, UUIDPrimaryKeyModel


class Notification(UUIDPrimaryKeyModel, TimeStampedModel):
    """
    In-app notification center entry. This, not email, is the system of
    record for 'has the student/officer been told' (system specification
    §14) — email delivery to Gambian carriers/ISPs cannot be assumed
    reliable, so the portal itself must carry the authoritative state.
    """

    class Channel(models.TextChoices):
        IN_APP = "in_app", "In-app"
        SMS = "sms", "SMS"  # reserved for Phase 2, unused at MVP
        WHATSAPP = "whatsapp", "WhatsApp"  # reserved for Phase 2, unused at MVP

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    channel = models.CharField(max_length=15, choices=Channel.choices, default=Channel.IN_APP)
    title = models.CharField(max_length=200)
    body = models.TextField()
    application = models.ForeignKey(
        "verification.Application", on_delete=models.CASCADE, null=True, blank=True, related_name="notifications"
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} -> {self.recipient.email}"


class EmailLog(UUIDPrimaryKeyModel):
    """
    Delivery record for every email sent (system specification §14) — the
    template used and delivery status, never the email body itself, since
    the body may reference application state that changes after send.
    """

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    recipient_email = models.EmailField()
    template_name = models.CharField(max_length=100)
    application = models.ForeignKey(
        "verification.Application", on_delete=models.SET_NULL, null=True, blank=True, related_name="email_logs"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)
    provider_message_id = models.CharField(max_length=255, blank=True)
    error_detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "email_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.template_name} -> {self.recipient_email} ({self.status})"
