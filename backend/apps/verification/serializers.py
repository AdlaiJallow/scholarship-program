from rest_framework import serializers

from apps.core.storage import get_signed_url

from .models import (
    Application,
    ApplicationStatusHistory,
    DocumentReview,
    DocumentVersion,
    RequiredDocument,
    SubmittedDocument,
)


class RequiredDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequiredDocument
        fields = [
            "id",
            "name",
            "description",
            "is_mandatory",
            "accepted_file_types",
            "max_file_size_bytes",
            "renewal_policy",
            "validity_days",
        ]


class DocumentVersionSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    uploaded_by_email = serializers.EmailField(source="uploaded_by.email", read_only=True)

    class Meta:
        model = DocumentVersion
        fields = [
            "id",
            "version_number",
            "original_filename",
            "content_type",
            "file_size_bytes",
            "uploaded_at",
            "uploaded_by_email",
            "scan_status",
            "download_url",
        ]

    def get_download_url(self, obj):
        request = self.context.get("request")
        if request is None:
            return None
        # Always resolve through the authenticated API endpoint, which
        # issues a short-lived signed URL — never a stored/public path
        # (system specification §16).
        from django.urls import reverse

        return request.build_absolute_uri(reverse("document-download", args=[obj.id]))


class DocumentReviewSerializer(serializers.ModelSerializer):
    officer_name = serializers.CharField(source="officer.full_name", read_only=True)

    class Meta:
        model = DocumentReview
        fields = ["id", "verdict", "comment", "officer_name", "created_at"]
        read_only_fields = ["id", "officer_name", "created_at"]


class SubmittedDocumentSerializer(serializers.ModelSerializer):
    required_document = RequiredDocumentSerializer(read_only=True)
    current_version = DocumentVersionSerializer(read_only=True)
    reviews = serializers.SerializerMethodField()

    class Meta:
        model = SubmittedDocument
        fields = ["id", "status", "required_document", "current_version", "reviews", "updated_at"]

    def get_reviews(self, obj):
        if obj.current_version_id is None:
            return []
        reviews = obj.current_version.reviews.all()
        return DocumentReviewSerializer(reviews, many=True, context=self.context).data


class ApplicationStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_email = serializers.EmailField(source="changed_by.email", read_only=True, default=None)

    class Meta:
        model = ApplicationStatusHistory
        fields = ["from_status", "to_status", "changed_by_email", "note", "created_at"]


class ScholarshipSummarySerializer(serializers.Serializer):
    scholarship_reference_id = serializers.CharField()
    scholarship_type = serializers.CharField(source="scholarship_type.name")
    institution = serializers.CharField(source="institution.name")
    country = serializers.CharField(source="country.name")
    program = serializers.CharField(source="program.name", default=None, allow_null=True)
    status = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class ApplicationListSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="scholarship.student.full_name", read_only=True)
    scholarship_id = serializers.CharField(source="scholarship.scholarship_reference_id", read_only=True)
    institution = serializers.CharField(source="scholarship.institution.name", read_only=True)
    country = serializers.CharField(source="scholarship.country.name", read_only=True)
    scholarship_type = serializers.CharField(source="scholarship.scholarship_type.name", read_only=True)
    assigned_officer_name = serializers.CharField(source="assigned_officer.full_name", read_only=True, default=None)

    class Meta:
        model = Application
        fields = [
            "id",
            "reference_number",
            "status",
            "student_name",
            "scholarship_id",
            "institution",
            "country",
            "scholarship_type",
            "assigned_officer_name",
            "submitted_at",
            "updated_at",
        ]


class ApplicationDetailSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="scholarship.student.full_name", read_only=True)
    student_email = serializers.EmailField(source="scholarship.student.user.email", read_only=True)
    student_dob = serializers.DateField(source="scholarship.student.date_of_birth", read_only=True)
    student_gender = serializers.CharField(source="scholarship.student.gender", read_only=True)
    student_phone = serializers.CharField(source="scholarship.student.phone_number", read_only=True)
    scholarship = ScholarshipSummarySerializer(read_only=True)
    submitted_documents = SubmittedDocumentSerializer(many=True, read_only=True)
    status_history = ApplicationStatusHistorySerializer(many=True, read_only=True)
    rejection_reason_display = serializers.CharField(source="get_rejection_reason_display", read_only=True)

    class Meta:
        model = Application
        fields = [
            "id",
            "reference_number",
            "status",
            "student_name",
            "student_email",
            "student_dob",
            "student_gender",
            "student_phone",
            "scholarship",
            "assigned_officer",
            "submitted_documents",
            "status_history",
            "declaration_confirmed_at",
            "submitted_at",
            "decided_at",
            "decision_remarks",
            "rejection_reason",
            "rejection_reason_display",
            "rejection_detail",
        ]


class ApproveApplicationSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
    confirm = serializers.BooleanField()

    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError("Approval must be explicitly confirmed.")
        return value


class RejectApplicationSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(choices=Application.RejectionReason.choices)
    detail = serializers.CharField(required=False, allow_blank=True, default="")
    confirm = serializers.BooleanField()

    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError("Rejection must be explicitly confirmed.")
        return value


class RequestInfoSerializer(serializers.Serializer):
    submitted_document_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class ReviewDocumentSerializer(serializers.Serializer):
    verdict = serializers.ChoiceField(choices=DocumentReview.Verdict.choices)
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class ReassignApplicationSerializer(serializers.Serializer):
    officer_id = serializers.IntegerField()
    reason = serializers.CharField(required=False, allow_blank=True, default="")
