"""
Document storage abstraction (system specification §16, §28): the API is
the only component with credentials to the store, and every document
access goes through a short-lived signed URL rather than a public path.
Backed by MinIO/S3 in production (DOCUMENT_STORAGE_BACKEND=s3); falls back
to local filesystem storage for development so the app runs without MinIO
running.
"""

import mimetypes
import os
import uuid

from django.conf import settings


def _s3_client():
    import boto3

    cfg = settings.DOCUMENT_STORAGE
    return boto3.client(
        "s3",
        endpoint_url=cfg["ENDPOINT_URL"],
        aws_access_key_id=cfg["ACCESS_KEY"],
        aws_secret_access_key=cfg["SECRET_KEY"],
        region_name=cfg["REGION"],
    )


def build_storage_key(application_id, required_document_id, filename):
    ext = os.path.splitext(filename)[1]
    return f"applications/{application_id}/{required_document_id}/{uuid.uuid4().hex}{ext}"


def store_uploaded_file(file_obj, storage_key):
    if settings.DOCUMENT_STORAGE_BACKEND == "s3":
        content_type = mimetypes.guess_type(storage_key)[0] or "application/octet-stream"
        _s3_client().upload_fileobj(
            file_obj,
            settings.DOCUMENT_STORAGE["BUCKET"],
            storage_key,
            ExtraArgs={"ContentType": content_type, "ServerSideEncryption": "AES256"},
        )
        return
    dest_path = settings.MEDIA_ROOT / storage_key
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "wb") as dest:
        for chunk in file_obj.chunks() if hasattr(file_obj, "chunks") else [file_obj.read()]:
            dest.write(chunk)


def get_signed_url(storage_key):
    if settings.DOCUMENT_STORAGE_BACKEND == "s3":
        cfg = settings.DOCUMENT_STORAGE
        return _s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": cfg["BUCKET"], "Key": storage_key},
            ExpiresIn=cfg["SIGNED_URL_EXPIRY_SECONDS"],
        )
    # Local dev fallback: served through the authenticated Django view itself,
    # not a public media URL — see verification.views.DocumentDownloadView.
    return None


def delete_object(storage_key):
    if settings.DOCUMENT_STORAGE_BACKEND == "s3":
        cfg = settings.DOCUMENT_STORAGE
        _s3_client().delete_object(Bucket=cfg["BUCKET"], Key=storage_key)
        return
    dest_path = settings.MEDIA_ROOT / storage_key
    if dest_path.exists():
        dest_path.unlink()
