"""
Content-sniffed file-type validation (system specification §13, §16) —
checks magic bytes, not just the filename extension or client-supplied
Content-Type, both of which are trivially spoofed.
"""

_SIGNATURES = {
    "pdf": [(b"%PDF-", 0)],
    "jpg": [(b"\xff\xd8\xff", 0)],
    "jpeg": [(b"\xff\xd8\xff", 0)],
    "png": [(b"\x89PNG\r\n\x1a\n", 0)],
}


class FileValidationError(Exception):
    pass


def sniff_file_type(head_bytes: bytes):
    for type_name, signatures in _SIGNATURES.items():
        for magic, offset in signatures:
            if head_bytes[offset : offset + len(magic)] == magic:
                return type_name
    return None


def validate_upload(file_obj, accepted_file_types, max_file_size_bytes):
    if file_obj.size > max_file_size_bytes:
        raise FileValidationError(
            f"This file is {file_obj.size / (1024 * 1024):.1f}MB; the limit for this document is "
            f"{max_file_size_bytes / (1024 * 1024):.1f}MB."
        )

    head = file_obj.read(16)
    file_obj.seek(0)
    detected_type = sniff_file_type(head)

    normalized_accepted = {t.lower().lstrip(".") for t in accepted_file_types}
    if detected_type is None or detected_type not in normalized_accepted:
        accepted_label = ", ".join(sorted(normalized_accepted))
        raise FileValidationError(
            f"This file doesn't look like an accepted format ({accepted_label}). "
            "It may be corrupted, mislabeled, or an unsupported file type."
        )
    return detected_type
