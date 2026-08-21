import re

from django.core.exceptions import ValidationError


class PasswordComplexityValidator:
    """Requires at least one uppercase, one lowercase, and one digit or symbol, on top of Django's length/common-password checks."""

    def validate(self, password, user=None):
        if not re.search(r"[A-Z]", password):
            raise ValidationError("Password must contain at least one uppercase letter.", code="password_no_upper")
        if not re.search(r"[a-z]", password):
            raise ValidationError("Password must contain at least one lowercase letter.", code="password_no_lower")
        if not re.search(r"[0-9\W]", password):
            raise ValidationError(
                "Password must contain at least one number or symbol.", code="password_no_number_or_symbol"
            )

    def get_help_text(self):
        return "Your password must be at least 12 characters and include an uppercase letter, a lowercase letter, and a number or symbol."
