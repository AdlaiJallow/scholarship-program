from celery import shared_task
from django.utils import timezone

from apps.core.scanning import ScanResult, scan_bytes


@shared_task
def scan_document_version(document_version_id):
    from .models import DocumentVersion

    version = DocumentVersion.objects.select_related("submitted_document").get(id=document_version_id)

    if version.submitted_document is None:
        return

    from django.conf import settings

    path = settings.MEDIA_ROOT / version.storage_key
    data = path.read_bytes() if path.exists() else b""

    result = scan_bytes(data)
    version.scan_status = {
        ScanResult.CLEAN: DocumentVersion.ScanStatus.CLEAN,
        ScanResult.INFECTED: DocumentVersion.ScanStatus.INFECTED,
        ScanResult.ERROR: DocumentVersion.ScanStatus.ERROR,
    }[result]
    version.scan_completed_at = timezone.now()
    version.save(update_fields=["scan_status", "scan_completed_at"])

    if result == ScanResult.INFECTED:
        from apps.audit.models import AuditLog
        from apps.audit.services import log_action

        log_action(
            AuditLog.Action.DOCUMENT_DELETED,
            target=version,
            metadata={"reason": "malware scan flagged this upload; quarantined"},
        )
