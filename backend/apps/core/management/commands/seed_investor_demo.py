import hashlib
from datetime import date, timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

# Minimal valid single-page PDF so downloads through DocumentDownloadView
# actually open in a browser/PDF viewer during a live demo, instead of a
# 0-byte stub.
PLACEHOLDER_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 150]/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n"
    b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"5 0 obj<</Length 60>>stream\n"
    b"BT /F1 14 Tf 20 100 Td (Demo document - sample only) Tj ET\n"
    b"endstream endobj\n"
    b"trailer<</Root 1 0 R>>"
)


class Command(BaseCommand):
    help = (
        "Seeds a full investor-demo dataset on top of seed_demo_data: extra "
        "institutions/scholarship types and five scholarship holders spread "
        "across every stage of the verification pipeline (in progress, "
        "under review, additional info required, rejected, approved), so "
        "the officer queue, student dashboard, notifications, and audit log "
        "all have realistic content to show."
    )

    def handle(self, *args, **options):
        call_command("seed_demo_data")

        from apps.accounts.models import Officer, Role, StudentPreRegistration, User
        from apps.catalog.models import Country, Institution, Program, ScholarshipType
        from apps.scholarships.models import Scholarship
        from apps.verification.models import Application, DocumentReview, RequiredDocument
        from apps.verification.services import (
            approve_application,
            get_current_application,
            missing_mandatory_documents,
            reject_application,
            request_additional_information,
            review_document,
            submit_application,
            upload_document,
        )
        from apps.core.storage import build_storage_key, store_uploaded_file
        from io import BytesIO

        # --- extra catalog data -------------------------------------------------
        ghana, _ = Country.objects.get_or_create(name="Ghana", defaults={"iso_code": "GHA"})
        morocco, _ = Country.objects.get_or_create(name="Morocco", defaults={"iso_code": "MAR"})
        uk, _ = Country.objects.get_or_create(name="United Kingdom", defaults={"iso_code": "GBR"})

        u_ghana, _ = Institution.objects.get_or_create(name="University of Ghana", country=ghana)
        akhawayn, _ = Institution.objects.get_or_create(name="Al Akhawayn University", country=morocco)
        westminster, _ = Institution.objects.get_or_create(name="University of Westminster", country=uk)

        cs_program, _ = Program.objects.get_or_create(
            name="BSc Computer Science", institution=u_ghana, academic_level=Program.AcademicLevel.UNDERGRADUATE
        )
        public_health, _ = Program.objects.get_or_create(
            name="MSc Public Health", institution=akhawayn, academic_level=Program.AcademicLevel.MASTERS
        )
        renewable_energy, _ = Program.objects.get_or_create(
            name="Diploma in Renewable Energy Technology",
            institution=westminster,
            academic_level=Program.AcademicLevel.DIPLOMA,
        )

        merit, _ = ScholarshipType.objects.get_or_create(name="Undergraduate Merit Scholarship")
        research, _ = ScholarshipType.objects.get_or_create(name="Graduate Research Scholarship")
        vocational, _ = ScholarshipType.objects.get_or_create(name="Technical/Vocational Scholarship")

        # --- second officer (supervisor) ----------------------------------------
        officer_role = Role.objects.get(name="Verification Officer")
        supervisor_role = Role.objects.get(name="Supervisor")

        officer_user = User.objects.get(email="officer@scholarships.gov.gm")
        officer = officer_user.officer_profile

        if not User.objects.filter(email="supervisor@scholarships.gov.gm").exists():
            supervisor_user = User.objects.create_user(
                email="supervisor@scholarships.gov.gm",
                password="ChangeMe123!",
                user_type=User.UserType.OFFICER,
                is_active=True,
            )
            supervisor = Officer.objects.create(
                user=supervisor_user, full_name="Binta Camara", employee_id="OFF-0002", role=supervisor_role
            )
            self.stdout.write(self.style.SUCCESS("Created supervisor: supervisor@scholarships.gov.gm / ChangeMe123!"))
        else:
            supervisor = User.objects.get(email="supervisor@scholarships.gov.gm").officer_profile

        if officer.supervisor_id != supervisor.id:
            officer.supervisor = supervisor
            officer.save(update_fields=["supervisor"])

        mandatory_docs = list(RequiredDocument.objects.filter(is_mandatory=True).order_by("name"))
        optional_docs = list(RequiredDocument.objects.filter(is_mandatory=False).order_by("name"))

        def make_student(mat_number, full_name, dob, gender, national_id, email, phone, institution_name):
            from apps.accounts.models import Student

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "user_type": User.UserType.STUDENT,
                    "is_active": True,
                    "email_verified_at": timezone.now(),
                },
            )
            if created:
                user.set_password("ChangeMe123!")
                user.save(update_fields=["password"])

            student, _ = Student.objects.get_or_create(
                user=user,
                defaults={
                    "full_name": full_name,
                    "date_of_birth": dob,
                    "gender": gender,
                    "national_id_number": national_id,
                    "phone_number": phone,
                    "address": "Banjul, The Gambia",
                },
            )

            pre_reg, _ = StudentPreRegistration.objects.get_or_create(
                mat_number=mat_number,
                defaults={
                    "full_name": full_name,
                    "date_of_birth": dob,
                    "email": email,
                    "phone_number": phone,
                    "institution_name": institution_name,
                    "imported_by": officer,
                },
            )
            if not pre_reg.activated_at:
                pre_reg.activated_at = timezone.now()
                pre_reg.activated_student = student
                pre_reg.save(update_fields=["activated_at", "activated_student"])

            return user, student

        def make_scholarship(mat_number, scholarship_type, institution, country, program, student, years=3):
            scholarship, _ = Scholarship.objects.get_or_create(
                scholarship_reference_id=mat_number,
                defaults={
                    "student": student,
                    "scholarship_type": scholarship_type,
                    "institution": institution,
                    "country": country,
                    "program": program,
                    "start_date": date(2024, 9, 1),
                    "end_date": date(2024, 9, 1) + timedelta(days=365 * years),
                },
            )
            if scholarship.student_id is None:
                scholarship.student = student
                scholarship.save(update_fields=["student"])
            return scholarship

        def upload_all(application, docs, student_user):
            slots = {}
            for req_doc in docs:
                filename = f"{req_doc.name.lower().replace(' ', '_').replace('/', '-')}.pdf"
                storage_key = build_storage_key(application.id, req_doc.id, filename)
                store_uploaded_file(BytesIO(PLACEHOLDER_PDF), storage_key)
                version = upload_document(
                    application,
                    req_doc,
                    {
                        "storage_key": storage_key,
                        "original_filename": filename,
                        "content_type": "application/pdf",
                        "file_size_bytes": len(PLACEHOLDER_PDF),
                        "checksum_sha256": hashlib.sha256(PLACEHOLDER_PDF).hexdigest(),
                    },
                    uploaded_by=student_user,
                )
                slots[req_doc.name] = version.submitted_document
            return slots

        by_name = {d.name: d for d in mandatory_docs + optional_docs}

        # NOTE: Application.reference_number is unique=True but defaults to ""
        # until submission, so at most one application system-wide can sit
        # unsubmitted at a time without an IntegrityError — see the
        # accompanying report. Worked around here by creating every
        # submitted application first and the one left in progress last.

        # 1. Awa Bojang — submitted, under review, partially verified by the officer.
        user, student = make_student(
            "20260003", "Awa Bojang", date(2001, 6, 3), "female", "GM-ID-100355",
            "awa.bojang@utg.edu.gm", "+220 700 0003", akhawayn.name,
        )
        scholarship = make_scholarship("20260003", research, akhawayn, morocco, public_health, student)
        application = get_current_application(scholarship)
        slots = upload_all(application, mandatory_docs + optional_docs, user)
        submit_application(application, user)
        application.assigned_officer = officer
        application.save(update_fields=["assigned_officer"])
        for name in ["Passport / National ID", "Admission Letter", "Enrollment Letter"]:
            slot = slots[name]
            review_document(slot.current_version, officer, DocumentReview.Verdict.VERIFIED, "Looks good.")

        # 3. Ousman Touray — additional information requested on one document.
        user, student = make_student(
            "20260004", "Ousman Touray", date(2000, 11, 9), "male", "GM-ID-100488",
            "ousman.touray@utg.edu.gm", "+220 700 0004", westminster.name,
        )
        scholarship = make_scholarship("20260004", vocational, westminster, uk, renewable_energy, student)
        application = get_current_application(scholarship)
        slots = upload_all(application, mandatory_docs, user)
        submit_application(application, user)
        application.assigned_officer = officer
        application.save(update_fields=["assigned_officer"])
        for name in ["Passport / National ID", "Enrollment Letter", "Proof of Registration", "Passport-size Photograph"]:
            review_document(slots[name].current_version, officer, DocumentReview.Verdict.VERIFIED, "Looks good.")
        transcript_slot = slots["Academic Transcript"]
        review_document(
            transcript_slot.current_version, officer, DocumentReview.Verdict.NEEDS_CLARIFICATION,
            "Scan is blurry — the grades are not legible.",
        )
        request_additional_information(
            application, officer, [transcript_slot.id],
            comment="Please re-upload a clearer scan of your academic transcript.",
        )

        # 4. Isatou Jallow — rejected: admission letter did not match the enrolled program.
        user, student = make_student(
            "20260005", "Isatou Jallow", date(2002, 3, 17), "female", "GM-ID-100592",
            "isatou.jallow@utg.edu.gm", "+220 700 0005", u_ghana.name,
        )
        scholarship = make_scholarship("20260005", merit, u_ghana, ghana, cs_program, student)
        application = get_current_application(scholarship)
        slots = upload_all(application, mandatory_docs, user)
        submit_application(application, user)
        application.assigned_officer = officer
        application.save(update_fields=["assigned_officer"])
        for name in ["Passport / National ID", "Academic Transcript", "Proof of Registration", "Passport-size Photograph"]:
            review_document(slots[name].current_version, officer, DocumentReview.Verdict.VERIFIED, "Looks good.")
        review_document(
            slots["Admission Letter"].current_version, officer, DocumentReview.Verdict.REJECTED,
            "Admission letter names a different program than the one on file.",
        )
        reject_application(
            application, officer, Application.RejectionReason.INFORMATION_MISMATCH,
            detail="Admission letter does not match the enrolled program (BSc Computer Science).",
        )

        # 5. Lamin Ceesay — fully approved.
        user, student = make_student(
            "20260006", "Lamin Ceesay", date(1999, 8, 25), "male", "GM-ID-100731",
            "lamin.ceesay@utg.edu.gm", "+220 700 0006", akhawayn.name,
        )
        scholarship = make_scholarship("20260006", research, akhawayn, morocco, public_health, student)
        application = get_current_application(scholarship)
        slots = upload_all(application, mandatory_docs + optional_docs, user)
        submit_application(application, user)
        application.assigned_officer = supervisor
        application.save(update_fields=["assigned_officer"])
        for name, slot in slots.items():
            review_document(slot.current_version, supervisor, DocumentReview.Verdict.VERIFIED, "Verified.")
        approve_application(application, supervisor, remarks="All documents verified. Congratulations!")

        # 6. Modou Drammeh — early stage, partially filled out, not yet submitted.
        # Created last: an unsubmitted application has reference_number=""
        # and that column is unique, so only one such row can exist at a time.
        user, student = make_student(
            "20260002", "Modou Drammeh", date(2003, 1, 20), "male", "GM-ID-100234",
            "modou.drammeh@utg.edu.gm", "+220 700 0002", u_ghana.name,
        )
        scholarship = make_scholarship("20260002", merit, u_ghana, ghana, cs_program, student)
        application = get_current_application(scholarship)
        upload_all(application, mandatory_docs[:3], user)

        self.stdout.write(self.style.SUCCESS(
            "Investor demo seed complete:\n"
            "  Super admin:   admin@scholarships.gov.gm / ChangeMe123!\n"
            "  Officer:       officer@scholarships.gov.gm / ChangeMe123!\n"
            "  Supervisor:    supervisor@scholarships.gov.gm / ChangeMe123!\n"
            "  Students (all / ChangeMe123!):\n"
            "    fatou.sanneh@utg.edu.gm      — not yet activated (mat 20260001, use the activation flow)\n"
            "    modou.drammeh@utg.edu.gm     — in progress, partially filled out\n"
            "    awa.bojang@utg.edu.gm        — submitted, under review\n"
            "    ousman.touray@utg.edu.gm     — additional information requested\n"
            "    isatou.jallow@utg.edu.gm     — rejected\n"
            "    lamin.ceesay@utg.edu.gm      — approved\n"
        ))
