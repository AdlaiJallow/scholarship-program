from django.urls import path

from . import reporting, views

urlpatterns = [
    # Student
    path("me/requirements", views.RequirementsView.as_view(), name="me-requirements"),
    path("me/documents", views.UploadDocumentView.as_view(), name="me-documents-upload"),
    path("me/documents/<int:submitted_document_id>", views.DeleteDocumentView.as_view(), name="me-documents-delete"),
    path("me/application/submit", views.SubmitApplicationView.as_view(), name="me-application-submit"),
    path("me/application/status", views.MyApplicationStatusView.as_view(), name="me-application-status"),
    path("documents/<uuid:version_id>/download", views.DocumentDownloadView.as_view(), name="document-download"),
    # Ministry admin
    path("admin/applications", views.ApplicationQueueView.as_view(), name="admin-applications-list"),
    path("admin/applications/<uuid:application_id>", views.ApplicationDetailView.as_view(), name="admin-applications-detail"),
    path("admin/applications/<uuid:application_id>/claim", views.ClaimApplicationView.as_view(), name="admin-applications-claim"),
    path(
        "admin/applications/<uuid:application_id>/documents/<int:submitted_document_id>/review",
        views.ReviewDocumentView.as_view(),
        name="admin-applications-review-document",
    ),
    path("admin/applications/<uuid:application_id>/approve", views.ApproveApplicationView.as_view(), name="admin-applications-approve"),
    path("admin/applications/<uuid:application_id>/reject", views.RejectApplicationView.as_view(), name="admin-applications-reject"),
    path(
        "admin/applications/<uuid:application_id>/request-information",
        views.RequestInfoView.as_view(),
        name="admin-applications-request-info",
    ),
    path("admin/applications/<uuid:application_id>/reassign", views.ReassignApplicationView.as_view(), name="admin-applications-reassign"),
    path("admin/document-requirements", views.RequiredDocumentAdminListCreateView.as_view(), name="admin-requirements-list"),
    path("admin/document-requirements/<int:pk>", views.RequiredDocumentAdminDetailView.as_view(), name="admin-requirements-detail"),
    path("admin/reports/summary", reporting.ReportsSummaryView.as_view(), name="admin-reports-summary"),
    path("admin/reports/breakdown", reporting.ReportsBreakdownView.as_view(), name="admin-reports-breakdown"),
    path("admin/reports/processing-time", reporting.ReportsProcessingTimeView.as_view(), name="admin-reports-processing-time"),
    path("admin/export", reporting.ExportView.as_view(), name="admin-export"),
]
