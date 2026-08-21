"""
Column-level encryption for identity fields (national ID / passport number)
per the security architecture in the system specification §16. Uses Fernet
(AES-128-CBC + HMAC) keyed from FIELD_ENCRYPTION_KEY so the value is opaque
in a database dump or backup even to someone with read access to Postgres
but not the application's key material.
"""

from django.conf import settings
from django.db import models


def _fernet():
    from cryptography.fernet import Fernet

    key = getattr(settings, "FIELD_ENCRYPTION_KEY", None)
    if not key:
        raise RuntimeError(
            "FIELD_ENCRYPTION_KEY is not set. Generate one with "
            "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"` "
            "and set it in the environment before storing encrypted fields."
        )
    return Fernet(key)


class EncryptedCharField(models.BinaryField):
    """Stores a CharField's value encrypted at rest; transparent to Python callers."""

    def __init__(self, *args, max_cleartext_length=255, **kwargs):
        self.max_cleartext_length = max_cleartext_length
        kwargs.setdefault("editable", True)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["max_cleartext_length"] = self.max_cleartext_length
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return _fernet().decrypt(bytes(value)).decode("utf-8")

    def to_python(self, value):
        if value is None or isinstance(value, str):
            return value
        return _fernet().decrypt(bytes(value)).decode("utf-8")

    def get_prep_value(self, value):
        if value is None:
            return value
        if isinstance(value, bytes):
            return value
        return _fernet().encrypt(str(value).encode("utf-8"))

    def formfield(self, **kwargs):
        from django import forms

        defaults = {"max_length": self.max_cleartext_length, "form_class": forms.CharField}
        defaults.update(kwargs)
        return super().formfield(**defaults)
