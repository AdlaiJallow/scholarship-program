"""
Malware scanning strategy (system specification §16): file-type validation
alone is not a security control — a valid PDF can carry an embedded
exploit. Production MUST set ANTIVIRUS_SCAN_BACKEND=clamav (or an
equivalent real scan engine) before launch; the "noop" backend exists only
so the upload pipeline is exercisable in local development without a
ClamAV daemon running, and always logs loudly that nothing was scanned.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class ScanResult:
    CLEAN = "clean"
    INFECTED = "infected"
    ERROR = "error"


def scan_bytes(data: bytes) -> str:
    backend = settings.ANTIVIRUS_SCAN_BACKEND
    if backend == "clamav":
        return _scan_with_clamav(data)
    logger.warning(
        "ANTIVIRUS_SCAN_BACKEND=noop — upload was NOT scanned for malware. "
        "This is only acceptable in local development; set ANTIVIRUS_SCAN_BACKEND=clamav before launch."
    )
    return ScanResult.CLEAN


def _scan_with_clamav(data: bytes) -> str:
    import io

    try:
        import clamd

        client = clamd.ClamdNetworkSocket(host=settings.CLAMAV_HOST, port=settings.CLAMAV_PORT)
        result = client.instream(io.BytesIO(data))
        status = result.get("stream", ("ERROR",))[0]
        if status == "OK":
            return ScanResult.CLEAN
        if status == "FOUND":
            return ScanResult.INFECTED
        return ScanResult.ERROR
    except Exception:  # noqa: BLE001 — a scan failure must fail closed, not silently pass the file
        logger.exception("ClamAV scan failed")
        return ScanResult.ERROR
