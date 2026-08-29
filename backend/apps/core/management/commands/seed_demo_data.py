from datetime import date

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seeds reference data, a Ministry super admin, and a demo student pre-registration for local development."

    def handle(self, *args, **options):
        from apps.accounts.models import Officer, Role, StudentPreRegistration, User
        from apps.catalog.models import Country, Institution, Program, ScholarshipType
        from apps.verification.models import RequiredDocument

        gambia, _ = Country.objects.get_or_create(name="The Gambia", defaults={"iso_code": "GMB"})
        senegal, _ = Country.objects.get_or_create(name="Senegal", defaults={"iso_code": "SEN"})

        uog, _ = Institution.objects.get_or_create(name="University of The Gambia", country=gambia)
        ucad, _ = Institution.objects.get_or_create(name="Université Cheikh Anta Diop", country=senegal)

        nursing, _ = Program.objects.get_or_create(
            name="Bachelor of Nursing Science", institution=ucad, academic_level=Program.AcademicLevel.UNDERGRADUATE
        )

        merit, _ = ScholarshipType.objects.get_or_create(name="Undergraduate Merit Scholarship")

        for name, mandatory in [
            ("Passport / National ID", True),
            ("Admission Letter", True),
            ("Enrollment Letter", True),
            ("Academic Transcript", True),
            ("Proof of Registration", True),
            ("Passport-size Photograph", True),
            ("Proof of Address", False),
        ]:
            RequiredDocument.objects.get_or_create(
                name=name,
                defaults={
                    "is_mandatory": mandatory,
                    "accepted_file_types": ["pdf", "jpg", "jpeg", "png"],
                    "max_file_size_bytes": 5 * 1024 * 1024,
                },
            )

        super_admin_role = Role.objects.get(name="Super Administrator")
        if not User.objects.filter(email="admin@scholarships.gov.gm").exists():
            admin_user = User.objects.create_superuser(email="admin@scholarships.gov.gm", password="ChangeMe123!")
            Officer.objects.create(
                user=admin_user, full_name="Ministry Super Admin", employee_id="ADM-0001", role=super_admin_role
            )
            self.stdout.write(self.style.SUCCESS("Created super admin: admin@scholarships.gov.gm / ChangeMe123!"))

        officer_role = Role.objects.get(name="Verification Officer")
        if not User.objects.filter(email="officer@scholarships.gov.gm").exists():
            officer_user = User.objects.create_user(
                email="officer@scholarships.gov.gm", password="ChangeMe123!", user_type=User.UserType.OFFICER, is_active=True
            )
            Officer.objects.create(
                user=officer_user, full_name="Lamin Jatta", employee_id="OFF-0001", role=officer_role
            )
            self.stdout.write(self.style.SUCCESS("Created officer: officer@scholarships.gov.gm / ChangeMe123!"))

        from apps.scholarships.models import Scholarship

        demo_mat_number = "20260001"
        Scholarship.objects.get_or_create(
            scholarship_reference_id=demo_mat_number,
            defaults={
                "scholarship_type": merit,
                "institution": ucad,
                "country": senegal,
                "program": nursing,
                "start_date": date(2024, 9, 1),
                "end_date": date(2027, 8, 31),
            },
        )

        if not StudentPreRegistration.objects.filter(mat_number=demo_mat_number).exists():
            StudentPreRegistration.objects.create(
                mat_number=demo_mat_number,
                full_name="Fatou Sanneh",
                date_of_birth=date(2002, 4, 12),
                email="fatou.sanneh@utg.edu.gm",
                phone_number="+220 700 0001",
                institution_name=ucad.name,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created pre-registration for mat_number={demo_mat_number}, "
                    "email=fatou.sanneh@utg.edu.gm — verification codes are now emailed on "
                    "demand via /auth/activation/verify-identity, not pre-set."
                )
            )

        self.stdout.write(self.style.SUCCESS("Demo data seed complete."))
