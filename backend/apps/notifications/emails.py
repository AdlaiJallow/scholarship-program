"""
Reusable email templates (system specification §27). Each template renders
from application state only — student name, application reference, current
status, the relevant action, portal link, Ministry contact — and never
embeds a document or unnecessary personal data in the email body itself.
"""

from django.conf import settings

TEMPLATES = {
    "submission_confirmation": {
        "subject": "Your scholarship verification application has been received — {reference_number}",
        "body": (
            "Dear {student_name},\n\n"
            "We have received your scholarship verification application, reference {reference_number}.\n"
            "It is now under review by the Ministry. You can track its status at any time.\n\n"
            "Portal: {portal_link}\n"
            "Ministry contact: {ministry_contact}\n"
        ),
    },
    "review_started": {
        "subject": "Your application {reference_number} is now under review",
        "body": (
            "Dear {student_name},\n\n"
            "A Ministry officer has begun reviewing your application, reference {reference_number}.\n"
            "No action is needed from you right now — we will notify you when a decision is made.\n\n"
            "Portal: {portal_link}\n"
            "Ministry contact: {ministry_contact}\n"
        ),
    },
    "info_requested": {
        "subject": "Action needed on your application {reference_number}",
        "body": (
            "Dear {student_name},\n\n"
            "The Ministry needs additional information before your application, reference {reference_number}, "
            "can be approved. Please sign in to the portal to see which document(s) need attention.\n\n"
            "Portal: {portal_link}\n"
            "Ministry contact: {ministry_contact}\n"
        ),
    },
    "approved": {
        "subject": "Your scholarship verification has been approved — {reference_number}",
        "body": (
            "Dear {student_name},\n\n"
            "Your scholarship verification application, reference {reference_number}, has been approved.\n\n"
            "Portal: {portal_link}\n"
            "Ministry contact: {ministry_contact}\n"
        ),
    },
    "rejected": {
        "subject": "Update on your application {reference_number}",
        "body": (
            "Dear {student_name},\n\n"
            "Your scholarship verification application, reference {reference_number}, was not approved.\n"
            "Reason: {reason}\n\n"
            "Please sign in to the portal to see full details and next steps.\n\n"
            "Portal: {portal_link}\n"
            "Ministry contact: {ministry_contact}\n"
        ),
    },
    "correction_requested": {
        "subject": "Please correct a document on application {reference_number}",
        "body": (
            "Dear {student_name},\n\n"
            "The following document needs correction on application {reference_number}: {document_name}.\n\n"
            "Portal: {portal_link}\n"
            "Ministry contact: {ministry_contact}\n"
        ),
    },
    "deadline_reminder": {
        "subject": "Reminder: {days_remaining} day(s) left to complete verification",
        "body": (
            "Dear {student_name},\n\n"
            "Your scholarship verification, reference {reference_number}, has {days_remaining} day(s) remaining "
            "before the deadline. Please complete any outstanding steps in the portal.\n\n"
            "Portal: {portal_link}\n"
            "Ministry contact: {ministry_contact}\n"
        ),
    },
}


def render(template_name, **context):
    template = TEMPLATES[template_name]
    context.setdefault("portal_link", settings.PORTAL_BASE_URL)
    context.setdefault("ministry_contact", settings.MINISTRY_CONTACT_EMAIL)
    return template["subject"].format(**context), template["body"].format(**context)
