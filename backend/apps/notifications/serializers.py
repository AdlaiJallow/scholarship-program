from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    application_reference = serializers.CharField(source="application.reference_number", read_only=True, default=None)

    class Meta:
        model = Notification
        fields = ["id", "title", "body", "is_read", "application_reference", "created_at"]
