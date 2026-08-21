"""
Workflow engine for the verification state machine (system specification
§5, §8, §9). All application status changes go through here — nowhere else
in the codebase should set Application.status directly — so the audit
trail, notifications, and history are never accidentally skipped.
"""

import hashlib
import secrets
from datetime import date

from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_action
from apps.audit.models import AuditLog

from .models import (
    Application,
    ApplicationStatusHistory,
    DocumentVersion,
    RequiredDocument,
    SubmittedDocument,
)


def generate_reference_number():
    year = date.today().year
    suffix = secrets.token_hex(4).upper()
    return f"SVP-{year}-{suffix}"


def get_current_application(scholarship):
    """
    Returns the scholarship's one ongoing verification cycle, creating it
    only if none exists yet. Deliberately does NOT start a new cycle just
    because the latest one is decided (approved/rejected) — re-verification
    is a distinct, explicit Ministry action (Phase 2+), not something a
    student dashboard view should trigger silently on every page load.
    """
    application = scholarship.applications.order_by("-created_at").first()
    if application is None:
        return Application.objects.create(scholarship=scholarship, status=Application.Status.IN_PROGRESS)
    if application.status == Application.Status.NOT_STARTED:
        application.status = Application.Status.IN_PROGRESS
        application.save(update_fields=["status", "updated_at"])
    return application


def _transition(application, to_status, actor=None, note="", request=None, audit_action=None):
    from_status = application.status
    application.status = to_status
    application.save(update_fields=["status", "updated_at"])
    ApplicationStatusHistory.objects.create(
        application=application, from_status=from_status, to_status=to_status, changed_by=actor, note=note
    )
    if audit_action:
        log_action(audit_action, actor=actor, target=application, metadata={"note": note}, request=request)
    return application


@transaction.atomic
def upload_document(application, required_document, file_meta, uploaded_by, request=None):
    """
    Records a new immutable DocumentVersion for a requirement slot and
    points the slot's current_version at it. Never overwrites a prior
    version (system specification §13, §22).
    """
    slot, _ = SubmittedDocument.objects.select_for_update().get_or_create(
        application=application, required_document=required_document
    )
    next_version_number = slot.versions.count() + 1
    version = DocumentVersion.objects.create(
        submitted_document=slot,
        version_number=next_version_number,
        storage_key=file_meta["storage_key"],
        original_filename=file_meta["original_filename"],
        content_type=file_meta["content_type"],
        file_size_bytes=file_meta["file_size_bytes"],
        checksum_sha256=file_meta["checksum_sha256"],
        uploaded_by=uploaded_by,
    )
    slot.current_version = version
    slot.status = SubmittedDocument.Status.PENDING
    slot.save(update_fields=["current_version", "status", "updated_at"])

    log_action(
        AuditLog.Action.DOCUMENT_UPLOADED,
        actor=uploaded_by,
        target=version,
        metadata={"required_document": required_document.name, "version": next_version_number},
        request=request,
    )
    return version


def missing_mandatory_documents(application):
    required = RequiredDocument.resolve_for_scholarship(application.scholarship).filter(is_mandatory=True)
    submitted_ids = set(
        application.submitted_documents.filter(current_version__isnull=False).values_list(
            "required_document_id", flat=True
        )
    )
    return required.exclude(id__in=submitted_ids)


@transaction.atomic
def submit_application(application, student_user, request=None):
    missing = missing_mandatory_documents(application)
    if missing.exists():
        raise ValueError(
            "Cannot submit: missing mandatory document(s): " + ", ".join(d.name for d in missing)
        )
    if not application.reference_number:
        application.reference_number = generate_reference_number()
    application.declaration_confirmed_at = timezone.now()
    application.submitted_at = timezone.now()
    application.save(update_fields=["reference_number", "declaration_confirmed_at", "submitted_at", "updated_at"])
    _transition(
        application,
        Application.Status.UNDER_REVIEW,
        actor=student_user,
        note="Student submitted application for review.",
        request=request,
        audit_action=AuditLog.Action.APPLICATION_SUBMITTED,
    )
    from apps.notifications.services import notify_application_submitted

    notify_application_submitted(application)
    return application


@transaction.atomic
def approve_application(application, officer, remarks="", request=None):
    application.decided_by = officer
    application.decided_at = timezone.now()
    application.decision_remarks = remarks
    application.save(update_fields=["decided_by", "decided_at", "decision_remarks", "updated_at"])
    _transition(
        application,
        Application.Status.APPROVED,
        actor=officer.user,
        note=remarks,
        request=request,
        audit_action=AuditLog.Action.APPLICATION_APPROVED,
    )
    from apps.notifications.services import notify_application_approved

    notify_application_approved(application)
    return application


@transaction.atomic
def reject_application(application, officer, reason, detail="", request=None):
    application.decided_by = officer
    application.decided_at = timezone.now()
    application.rejection_reason = reason
    application.rejection_detail = detail
    application.save(
        update_fields=["decided_by", "decided_at", "rejection_reason", "rejection_detail", "updated_at"]
    )
    _transition(
        application,
        Application.Status.REJECTED,
        actor=officer.user,
        note=detail,
        request=request,
        audit_action=AuditLog.Action.APPLICATION_REJECTED,
    )
    from apps.notifications.services import notify_application_rejected

    notify_application_rejected(application)
    return application


@transaction.atomic
def request_additional_information(application, officer, submitted_document_ids, comment="", request=None):
    """Reopens only the flagged document slots for correction — not the whole application (system specification §5)."""
    slots = application.submitted_documents.filter(id__in=submitted_document_ids)
    slots.update(status=SubmittedDocument.Status.NEEDS_CLARIFICATION)
    _transition(
        application,
        Application.Status.ADDITIONAL_INFO_REQUIRED,
        actor=officer.user,
        note=comment,
        request=request,
        audit_action=AuditLog.Action.APPLICATION_INFO_REQUESTED,
    )
    from apps.notifications.services import notify_additional_information_requested

    notify_additional_information_requested(application, list(slots))
    return application


@transaction.atomic
def resubmit_application(application, student_user, request=None):
    """Student has corrected the flagged documents and is sending the application back for review."""
    if application.status not in {Application.Status.ADDITIONAL_INFO_REQUIRED, Application.Status.RESUBMISSION_REQUIRED}:
        raise ValueError("Application is not awaiting resubmission.")
    _transition(
        application,
        Application.Status.UNDER_REVIEW,
        actor=student_user,
        note="Student resubmitted corrected documents.",
        request=request,
        audit_action=AuditLog.Action.APPLICATION_RESUBMITTED,
    )
    return application


def review_document(document_version, officer, verdict, comment="", request=None):
    from .models import DocumentReview

    review = DocumentReview.objects.create(
        document_version=document_version, officer=officer, verdict=verdict, comment=comment
    )
    slot = document_version.submitted_document
    slot.status = verdict
    slot.save(update_fields=["status", "updated_at"])
    log_action(
        AuditLog.Action.DOCUMENT_REVIEWED,
        actor=officer.user,
        target=document_version,
        metadata={"verdict": verdict, "comment": comment},
        request=request,
    )
    return review


def sha256_of(file_obj):
    hasher = hashlib.sha256()
    for chunk in file_obj.chunks() if hasattr(file_obj, "chunks") else iter(lambda: file_obj.read(65536), b""):
        hasher.update(chunk)
    file_obj.seek(0)
    return hasher.hexdigest()
