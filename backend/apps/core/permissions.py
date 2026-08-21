from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsStudent(BasePermission):
    message = "This endpoint is only available to scholarship holders."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.user_type == "student")


class IsOfficerRole(BasePermission):
    """Any Ministry role: verification officer, supervisor, super admin, read-only reporting officer."""

    message = "This endpoint is only available to Ministry staff."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.user_type == "officer")


class HasRolePermission(BasePermission):
    """
    Checks the authenticated officer's Role for a named permission codename
    (e.g. "applications.approve"), per the RBAC model in the system
    specification §12 — a many-to-many Roles<->Permissions table rather than
    hard-coded role name checks scattered through view code.
    """

    required_permission = None

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.user_type == "officer"):
            return False
        officer = getattr(request.user, "officer_profile", None)
        if officer is None or officer.role is None:
            return False
        required = getattr(view, "required_permission", self.required_permission)
        if required is None:
            return True
        return officer.role.permissions.filter(codename=required).exists()


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
