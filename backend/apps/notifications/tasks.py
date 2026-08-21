import logging

from celery import shared_task
from django.core.mail import send_mail

from .emails import render
from .models import EmailLog

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_templated_email(self, email_log_id, template_name, recipient_email, context):
    log = EmailLog.objects.get(id=email_log_id)
    try:
        subject, body = render(template_name, **context)
        from django.conf import settings

        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient_email], fail_silently=False)
        log.status = EmailLog.Status.SENT
        from django.utils import timezone

        log.sent_at = timezone.now()
        log.save(update_fields=["status", "sent_at"])
    except Exception as exc:  # noqa: BLE001 — must record failure before deciding whether to retry
        log.status = EmailLog.Status.FAILED
        log.error_detail = str(exc)
        log.save(update_fields=["status", "error_detail"])
        logger.exception("Failed to send email %s to %s", template_name, recipient_email)
        raise self.retry(exc=exc)
