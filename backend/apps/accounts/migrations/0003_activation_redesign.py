import uuid

import django.db.models.deletion
from django.db import migrations, models

import apps.accounts.models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_seed_roles_permissions"),
    ]

    operations = [
        migrations.RenameField(
            model_name="studentpreregistration",
            old_name="scholarship_id",
            new_name="mat_number",
        ),
        migrations.AlterField(
            model_name="studentpreregistration",
            name="mat_number",
            field=models.CharField(
                max_length=8, unique=True, validators=[apps.accounts.models.mat_number_validator]
            ),
        ),
        migrations.RemoveField(
            model_name="studentpreregistration",
            name="activation_code_hash",
        ),
        migrations.RemoveField(
            model_name="studentpreregistration",
            name="activation_code_channel",
        ),
        migrations.RemoveField(
            model_name="studentpreregistration",
            name="activation_code_expires_at",
        ),
        migrations.RemoveField(
            model_name="studentpreregistration",
            name="activation_attempts",
        ),
        migrations.RemoveField(
            model_name="studentpreregistration",
            name="max_activation_attempts",
        ),
        migrations.CreateModel(
            name="EmailVerificationCode",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email", models.EmailField(max_length=254)),
                ("code_hash", models.CharField(max_length=255)),
                ("expires_at", models.DateTimeField()),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("max_attempts", models.PositiveIntegerField(default=5)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("invalidated_at", models.DateTimeField(blank=True, null=True)),
                ("requested_ip", models.GenericIPAddressField(blank=True, null=True)),
                (
                    "pre_registration",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="verification_codes",
                        to="accounts.studentpreregistration",
                    ),
                ),
            ],
            options={
                "db_table": "email_verification_codes",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="emailverificationcode",
            index=models.Index(fields=["pre_registration", "created_at"], name="email_verif_pre_reg_4aed5b_idx"),
        ),
    ]
