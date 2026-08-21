from django.db import migrations

# RBAC seed matching the role/permission table in the system specification
# §12 — codes are checked by apps.core.permissions.HasRolePermission, not
# hard-coded role-name comparisons, so a committee can regrant these later
# through the admin without a deployment.
ROLE_PERMISSIONS = {
    "Super Administrator": [
        "applications.approve",
        "applications.reject",
        "applications.request_info",
        "applications.reassign",
        "documents.review",
        "requirements.manage",
        "reports.view",
        "exports.run",
    ],
    "Verification Officer": [
        "applications.approve",
        "applications.reject",
        "applications.request_info",
        "documents.review",
    ],
    "Supervisor": [
        "applications.approve",
        "applications.reject",
        "applications.request_info",
        "applications.reassign",
        "documents.review",
        "reports.view",
    ],
    "Read-Only/Reporting Officer": [
        "reports.view",
        "exports.run",
    ],
}

PERMISSION_DESCRIPTIONS = {
    "applications.approve": "Approve a verification application",
    "applications.reject": "Reject a verification application",
    "applications.request_info": "Request additional information from a student",
    "applications.reassign": "Reassign an application to a different officer",
    "documents.review": "Mark a submitted document verified/rejected/needs clarification",
    "requirements.manage": "Configure required-document rules",
    "reports.view": "View statistics and reports",
    "exports.run": "Generate Excel/CSV exports",
}


def seed(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Permission = apps.get_model("accounts", "Permission")

    permissions_by_code = {}
    for codename, description in PERMISSION_DESCRIPTIONS.items():
        permission, _ = Permission.objects.get_or_create(codename=codename, defaults={"description": description})
        permissions_by_code[codename] = permission

    for role_name, codenames in ROLE_PERMISSIONS.items():
        role, _ = Role.objects.get_or_create(name=role_name, defaults={"is_system_role": True})
        for codename in codenames:
            permissions_by_code[codename].roles.add(role)


def unseed(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Role.objects.filter(name__in=ROLE_PERMISSIONS.keys(), is_system_role=True).delete()


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
