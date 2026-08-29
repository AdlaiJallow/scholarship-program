from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    EmailVerificationCode,
    FailedLoginAttempt,
    Officer,
    Permission,
    Role,
    Student,
    StudentPreRegistration,
    User,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    filter_horizontal = ()
    list_display = ("email", "user_type", "is_active", "is_staff", "created_at")
    list_filter = ("user_type", "is_active", "is_staff")
    search_fields = ("email",)
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Type & status", {"fields": ("user_type", "is_active", "is_staff", "is_superuser", "must_change_password")}),
        ("Important dates", {"fields": ("last_login", "created_at")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "user_type", "password1", "password2")}),
    )
    readonly_fields = ("created_at",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "is_system_role")
    search_fields = ("name",)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("codename", "description")
    filter_horizontal = ("roles",)
    search_fields = ("codename",)


@admin.register(Officer)
class OfficerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "employee_id", "role", "supervisor", "is_on_leave")
    list_filter = ("role", "is_on_leave")
    search_fields = ("full_name", "employee_id")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("full_name", "date_of_birth", "phone_number")
    search_fields = ("full_name",)


@admin.register(StudentPreRegistration)
class StudentPreRegistrationAdmin(admin.ModelAdmin):
    list_display = ("mat_number", "full_name", "is_activated_display", "created_at")
    search_fields = ("mat_number", "full_name", "email")
    readonly_fields = ("activated_at", "activated_student")

    @admin.display(description="Activated", boolean=True)
    def is_activated_display(self, obj):
        return obj.is_activated


@admin.register(EmailVerificationCode)
class EmailVerificationCodeAdmin(admin.ModelAdmin):
    list_display = ("pre_registration", "email", "created_at", "expires_at", "used_at", "invalidated_at", "attempts")
    search_fields = ("pre_registration__mat_number", "email")
    readonly_fields = (
        "pre_registration",
        "email",
        "code_hash",
        "attempts",
        "used_at",
        "invalidated_at",
        "created_at",
        "expires_at",
    )

    def has_add_permission(self, request):
        return False


@admin.register(FailedLoginAttempt)
class FailedLoginAttemptAdmin(admin.ModelAdmin):
    list_display = ("email", "ip_address", "attempted_at")
    search_fields = ("email", "ip_address")

    def has_add_permission(self, request):
        return False
