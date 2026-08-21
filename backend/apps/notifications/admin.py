from django.contrib import admin

from .models import EmailLog, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "recipient", "application", "is_read", "created_at")
    list_filter = ("is_read", "channel")
    search_fields = ("recipient__email", "title")


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("template_name", "recipient_email", "status", "created_at", "sent_at")
    list_filter = ("status", "template_name")
    search_fields = ("recipient_email",)
    readonly_fields = [f.name for f in EmailLog._meta.fields]

    def has_add_permission(self, request):
        return False
