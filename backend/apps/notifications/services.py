from .models import EmailLog, Notification
from .tasks import send_templated_email


def _student_user(application):
    return application.scholarship.student.user


def _dispatch(application, template_name, title, body, context):
    student = application.scholarship.student
    Notification.objects.create(
        recipient=student.user, title=title, body=body, application=application
    )
    email_log = EmailLog.objects.create(
        recipient_email=student.user.email, template_name=template_name, application=application
    )
    context = {
        "student_name": student.full_name,
        "reference_number": application.reference_number or "(not yet assigned)",
        **context,
    }
    send_templated_email.delay(str(email_log.id), template_name, student.user.email, context)


def notify_application_submitted(application):
    _dispatch(
        application,
        "submission_confirmation",
        "Application received",
        f"Your application {application.reference_number} has been received and is queued for review.",
        {},
    )


def notify_additional_information_requested(application, flagged_slots):
    doc_names = ", ".join(s.required_document.name for s in flagged_slots)
    _dispatch(
        application,
        "info_requested",
        "Action needed on your application",
        f"Please correct the following document(s): {doc_names}.",
        {},
    )
    for slot in flagged_slots:
        Notification.objects.create(
            recipient=_student_user(application),
            title="Document needs correction",
            body=f"{slot.required_document.name} needs correction.",
            application=application,
        )


def notify_application_approved(application):
    _dispatch(
        application,
        "approved",
        "Application approved",
        f"Application {application.reference_number} has been approved.",
        {},
    )


def notify_application_rejected(application):
    reason_label = application.get_rejection_reason_display() if application.rejection_reason else "See portal for details"
    _dispatch(
        application,
        "rejected",
        "Application rejected",
        f"Application {application.reference_number} was rejected: {reason_label}.",
        {"reason": reason_label},
    )


def notify_deadline_approaching(application, days_remaining):
    _dispatch(
        application,
        "deadline_reminder",
        "Verification deadline approaching",
        f"{days_remaining} day(s) remaining to complete verification.",
        {"days_remaining": days_remaining},
    )
