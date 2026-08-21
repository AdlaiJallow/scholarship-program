from django.contrib import admin
from django.urls import include, path

# Deliberately no static()/MEDIA_URL serving here, even in DEBUG: uploaded
# documents must only ever be reachable through the authorized
# verification.views.DocumentDownloadView, never a public media path
# (system specification §16).
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.verification.urls")),
    path("api/v1/", include("apps.catalog.urls")),
    path("api/v1/", include("apps.notifications.urls")),
]
