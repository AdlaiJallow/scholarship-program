from django.conf import settings
from django.core.mail import send_mail


def send_activation_code_email(pre_registration, raw_code, is_resend=False):
    subject = "Your Scholarship Portal verification code"
    intro = "Your new verification code is" if is_resend else "Your verification code is"
    resend_note = "Your previous code is no longer valid. " if is_resend else ""
    body = (
        f"Hello {pre_registration.full_name},\n\n"
        f"{intro}: {raw_code}\n\n"
        f"{resend_note}This code expires in 24 hours and can only be used once. Enter it in "
        "the Scholarship Portal to finish activating your account.\n\n"
        "Do not share this code with anyone.\n\n"
        "If you didn't request this, you can safely ignore this email.\n\n"
        f"Ministry contact: {settings.MINISTRY_CONTACT_EMAIL} / {settings.MINISTRY_CONTACT_PHONE}\n"
    )
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [pre_registration.email], fail_silently=False)
