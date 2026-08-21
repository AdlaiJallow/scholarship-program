from django.urls import path

from . import views

urlpatterns = [
    path("me/notifications", views.MyNotificationsView.as_view(), name="me-notifications"),
    path("me/notifications/<uuid:notification_id>/read", views.MarkNotificationReadView.as_view(), name="me-notifications-read"),
]
