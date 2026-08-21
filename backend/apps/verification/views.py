import django_filters
from django.http import FileResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import Officer
from apps.audit.models import AuditLog
from apps.audit.services import log_action
from apps.core.permissions import HasRolePermission, IsOfficerRole, IsStudent
from apps.core.storage import build_storage_key, get_signed_url, store_uploaded_file
from apps.core.validation import FileValidationError, validate_upload

from . import services
from .models import Application, DocumentVersion, RequiredDocument, SubmittedDocument
from .serializers import (
    ApplicationDetailSerializer,
    ApplicationListSerializer,
    ApproveApplicationSerializer,
    ReassignApplicationSerializer,
    RejectApplicationSerializer,
    RequestInfoSerializer,
    RequiredDocumentSerializer,
    ReviewDocumentSerializer,
    SubmittedDocumentSerializer,
)


def _officer_can_access_application(officer, application):
    if officer.role.name == "Verification Officer":
        return application.assigned_officer_id in (None, officer.id)
    return True  # Supervisor, Super Administrator, Read-Only/Reporting Officer see all applications


def _active_scholarship_or_404(student):
    scholarship = student.scholarships.order_by("-created_at").first()
    if scholarship is None:
        from rest_framework.exceptions import NotFound

        raise NotFound("No scholarship record is associated with this account.")
    return scholarship


# ---------------------------------------------------------------------------
# Student-facing endpoints
# ---------------------------------------------------------------------------


class RequirementsView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        scholarship = _active_scholarship_or_404(request.user.student_profile)
        application = services.get_current_application(scholarship)
        required_docs = RequiredDocument.resolve_for_scholarship(scholarship)
        slots_by_doc = {
            s.required_document_id: s for s in application.submitted_documents.select_related("current_version")
        }
        results = []
        for doc in required_docs:
            slot = slots_by_doc.get(doc.id)
            results.append(
                {
                    "required_document": RequiredDocumentSerializer(doc).data,
                    "submitted": SubmittedDocumentSerializer(slot, context={"request": request}).data
                    if slot
                    else None,
                }
            )
        return Response({"application_id": application.id, "application_status": application.status, "requirements": results})


class UploadDocumentView(APIView):
    permission_classes = [IsStudent]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "document-upload"

    def post(self, request):
        scholarship = _active_scholarship_or_404(request.user.student_profile)
        application = services.get_current_application(scholarship)
        if not application.is_editable_by_student:
            return Response(
                {"detail": "This application is not currently open for document changes."},
                status=status.HTTP_409_CONFLICT,
            )

        required_document_id = request.data.get("required_document_id")
        file_obj = request.FILES.get("file")
        if not required_document_id or not file_obj:
            return Response({"detail": "required_document_id and file are required."}, status=status.HTTP_400_BAD_REQUEST)

        required_document = get_object_or_404(
            RequiredDocument.resolve_for_scholarship(scholarship), pk=required_document_id
        )

        try:
            validate_upload(file_obj, required_document.accepted_file_types, required_document.max_file_size_bytes)
        except FileValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        storage_key = build_storage_key(application.id, required_document.id, file_obj.name)
        store_uploaded_file(file_obj, storage_key)
        checksum = services.sha256_of(file_obj)

        version = services.upload_document(
            application,
            required_document,
            {
                "storage_key": storage_key,
                "original_filename": file_obj.name,
                "content_type": file_obj.content_type or "application/octet-stream",
                "file_size_bytes": file_obj.size,
                "checksum_sha256": checksum,
            },
            uploaded_by=request.user,
            request=request,
        )

        from .tasks import scan_document_version

        scan_document_version.delay(str(version.id))

        slot = version.submitted_document
        return Response(SubmittedDocumentSerializer(slot, context={"request": request}).data, status=status.HTTP_201_CREATED)


class DeleteDocumentView(APIView):
    permission_classes = [IsStudent]

    def delete(self, request, submitted_document_id):
        slot = get_object_or_404(
            SubmittedDocument,
            pk=submitted_document_id,
            application__scholarship__student=request.user.student_profile,
        )
        if not slot.application.is_editable_by_student:
            return Response(
                {"detail": "This application is not currently open for document changes."},
                status=status.HTTP_409_CONFLICT,
            )
        log_action(AuditLog.Action.DOCUMENT_DELETED, actor=request.user, target=slot, request=request)
        slot.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubmitApplicationView(APIView):
    permission_classes = [IsStudent]

    def post(self, request):
        scholarship = _active_scholarship_or_404(request.user.student_profile)
        application = services.get_current_application(scholarship)
        if not application.is_editable_by_student:
            return Response(
                {"detail": "This application has already been decided and cannot be resubmitted."},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            if application.status in (Application.Status.ADDITIONAL_INFO_REQUIRED, Application.Status.RESUBMISSION_REQUIRED):
                services.resubmit_application(application, request.user, request=request)
            else:
                services.submit_application(application, request.user, request=request)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ApplicationDetailSerializer(application, context={"request": request}).data)


class MyApplicationStatusView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        scholarship = _active_scholarship_or_404(request.user.student_profile)
        application = scholarship.applications.order_by("-created_at").first()
        if application is None:
            return Response({"status": Application.Status.NOT_STARTED})
        return Response(ApplicationDetailSerializer(application, context={"request": request}).data)


class DocumentDownloadView(APIView):
    """
    Authorized document access (system specification §16): no public URLs.
    Every fetch is an authorized API call. In production (S3 backend) this
    redirects to a one-time signed URL; in local filesystem development it
    streams the file directly, still behind the same authorization check.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, version_id):
        version = get_object_or_404(DocumentVersion, pk=version_id)
        application = version.submitted_document.application
        is_owning_student = (
            request.user.user_type == "student"
            and application.scholarship.student_id == getattr(request.user.student_profile, "id", None)
        )
        is_permitted_officer = request.user.user_type == "officer" and _officer_can_access_application(
            request.user.officer_profile, application
        )
        if not (is_owning_student or is_permitted_officer):
            return Response(status=status.HTTP_403_FORBIDDEN)

        log_action(AuditLog.Action.DOCUMENT_VIEWED, actor=request.user, target=version, request=request)

        signed_url = get_signed_url(version.storage_key)
        if signed_url:
            return HttpResponseRedirect(signed_url)

        from django.conf import settings

        path = settings.MEDIA_ROOT / version.storage_key
        return FileResponse(open(path, "rb"), content_type=version.content_type, filename=version.original_filename)


# ---------------------------------------------------------------------------
# Ministry admin endpoints
# ---------------------------------------------------------------------------


class RequiredDocumentAdminListCreateView(generics.ListCreateAPIView):
    """Document-requirement configuration (system specification §13) — a Ministry admin form, not a code change."""

    permission_classes = [HasRolePermission]
    required_permission = "requirements.manage"
    serializer_class = RequiredDocumentSerializer
    queryset = RequiredDocument.objects.all()

    def perform_create(self, serializer):
        instance = serializer.save()
        log_action(AuditLog.Action.REQUIREMENT_CONFIGURED, actor=self.request.user, target=instance, request=self.request)


class RequiredDocumentAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [HasRolePermission]
    required_permission = "requirements.manage"
    serializer_class = RequiredDocumentSerializer
    queryset = RequiredDocument.objects.all()

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(AuditLog.Action.REQUIREMENT_CONFIGURED, actor=self.request.user, target=instance, request=self.request)


class ApplicationFilter(django_filters.FilterSet):
    institution = django_filters.NumberFilter(field_name="scholarship__institution_id")
    country = django_filters.NumberFilter(field_name="scholarship__country_id")
    scholarship_type = django_filters.NumberFilter(field_name="scholarship__scholarship_type_id")
    status = django_filters.CharFilter(field_name="status")
    submitted_after = django_filters.DateFilter(field_name="submitted_at", lookup_expr="gte")
    submitted_before = django_filters.DateFilter(field_name="submitted_at", lookup_expr="lte")

    class Meta:
        model = Application
        fields = ["institution", "country", "scholarship_type", "status", "submitted_after", "submitted_before"]


class ApplicationQueueView(generics.ListAPIView):
    permission_classes = [IsOfficerRole]
    serializer_class = ApplicationListSerializer
    filterset_class = ApplicationFilter
    search_fields = ["reference_number", "scholarship__scholarship_reference_id", "scholarship__student__full_name"]
    ordering_fields = ["submitted_at", "updated_at"]

    def get_queryset(self):
        officer = self.request.user.officer_profile
        qs = Application.objects.select_related(
            "scholarship__student", "scholarship__institution", "scholarship__country", "scholarship__scholarship_type", "assigned_officer"
        ).exclude(status=Application.Status.NOT_STARTED)
        if officer.role.name == "Verification Officer":
            from django.db.models import Q

            qs = qs.filter(Q(assigned_officer=officer) | Q(assigned_officer__isnull=True))
        return qs


class ApplicationDetailView(APIView):
    permission_classes = [IsOfficerRole]

    def get(self, request, application_id):
        application = get_object_or_404(
            Application.objects.select_related("scholarship__student__user", "scholarship__institution", "scholarship__country", "scholarship__scholarship_type"),
            pk=application_id,
        )
        if not _officer_can_access_application(request.user.officer_profile, application):
            return Response(status=status.HTTP_403_FORBIDDEN)
        log_action(AuditLog.Action.APPLICATION_VIEWED, actor=request.user, target=application, request=request)
        return Response(ApplicationDetailSerializer(application, context={"request": request}).data)


class ClaimApplicationView(APIView):
    permission_classes = [IsOfficerRole]

    def post(self, request, application_id):
        application = get_object_or_404(Application, pk=application_id, assigned_officer__isnull=True)
        application.assigned_officer = request.user.officer_profile
        application.save(update_fields=["assigned_officer", "updated_at"])
        return Response(ApplicationDetailSerializer(application, context={"request": request}).data)


class ReviewDocumentView(APIView):
    permission_classes = [HasRolePermission]
    required_permission = "documents.review"

    def post(self, request, application_id, submitted_document_id):
        slot = get_object_or_404(SubmittedDocument, pk=submitted_document_id, application_id=application_id)
        if not _officer_can_access_application(request.user.officer_profile, slot.application):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if slot.current_version_id is None:
            return Response({"detail": "No document has been uploaded for this requirement yet."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ReviewDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.review_document(
            slot.current_version,
            request.user.officer_profile,
            serializer.validated_data["verdict"],
            serializer.validated_data["comment"],
            request=request,
        )
        return Response(SubmittedDocumentSerializer(slot, context={"request": request}).data, status=status.HTTP_201_CREATED)


class ApproveApplicationView(APIView):
    permission_classes = [HasRolePermission]
    required_permission = "applications.approve"

    def post(self, request, application_id):
        application = get_object_or_404(Application, pk=application_id)
        if not _officer_can_access_application(request.user.officer_profile, application):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = ApproveApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.approve_application(
            application, request.user.officer_profile, serializer.validated_data["remarks"], request=request
        )
        return Response(ApplicationDetailSerializer(application, context={"request": request}).data)


class RejectApplicationView(APIView):
    permission_classes = [HasRolePermission]
    required_permission = "applications.reject"

    def post(self, request, application_id):
        application = get_object_or_404(Application, pk=application_id)
        if not _officer_can_access_application(request.user.officer_profile, application):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = RejectApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.reject_application(
            application,
            request.user.officer_profile,
            serializer.validated_data["reason"],
            serializer.validated_data["detail"],
            request=request,
        )
        return Response(ApplicationDetailSerializer(application, context={"request": request}).data)


class RequestInfoView(APIView):
    permission_classes = [HasRolePermission]
    required_permission = "applications.request_info"

    def post(self, request, application_id):
        application = get_object_or_404(Application, pk=application_id)
        if not _officer_can_access_application(request.user.officer_profile, application):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = RequestInfoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_additional_information(
            application,
            request.user.officer_profile,
            serializer.validated_data["submitted_document_ids"],
            serializer.validated_data["comment"],
            request=request,
        )
        return Response(ApplicationDetailSerializer(application, context={"request": request}).data)


class ReassignApplicationView(APIView):
    permission_classes = [HasRolePermission]
    required_permission = "applications.reassign"

    def post(self, request, application_id):
        application = get_object_or_404(Application, pk=application_id)
        serializer = ReassignApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_officer = get_object_or_404(Officer, pk=serializer.validated_data["officer_id"])
        previous_officer = application.assigned_officer
        application.assigned_officer = new_officer
        application.save(update_fields=["assigned_officer", "updated_at"])
        log_action(
            AuditLog.Action.APPLICATION_REASSIGNED,
            actor=request.user,
            target=application,
            metadata={
                "from_officer": previous_officer.employee_id if previous_officer else None,
                "to_officer": new_officer.employee_id,
                "reason": serializer.validated_data["reason"],
            },
            request=request,
        )
        return Response(ApplicationDetailSerializer(application, context={"request": request}).data)
