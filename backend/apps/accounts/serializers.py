from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Officer, Student

UTG_EMAIL_SUFFIX = "@utg.edu.gm"


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class VerifyIdentitySerializer(serializers.Serializer):
    mat_number = serializers.RegexField(
        r"^\d{8}$", error_messages={"invalid": "MAT number must be exactly 8 digits."}
    )
    utg_email = serializers.EmailField()

    def validate_utg_email(self, value):
        if not value.lower().endswith(UTG_EMAIL_SUFFIX):
            raise serializers.ValidationError(f"Please use your UTG email address (ending in {UTG_EMAIL_SUFFIX}).")
        return value


class ResendCodeSerializer(VerifyIdentitySerializer):
    pass


class VerifyCodeSerializer(VerifyIdentitySerializer):
    code = serializers.CharField(min_length=6, max_length=8)


class CreateAccountSerializer(serializers.Serializer):
    verification_token = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    phone_number = serializers.CharField(required=False, allow_blank=True, default="")
    address = serializers.CharField(required=False, allow_blank=True, default="")
    gender = serializers.ChoiceField(choices=Student.Gender.choices, required=False, allow_blank=True, default="")

    def validate_password(self, value):
        validate_password(value)
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class StudentProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Student
        fields = ["full_name", "date_of_birth", "gender", "phone_number", "address", "email"]
        read_only_fields = fields


class OfficerProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    role = serializers.CharField(source="role.name", read_only=True)

    class Meta:
        model = Officer
        fields = ["full_name", "employee_id", "department", "role", "email"]
        read_only_fields = fields
