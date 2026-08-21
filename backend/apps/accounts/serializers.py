from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Officer, Student


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class ActivateSerializer(serializers.Serializer):
    scholarship_id = serializers.CharField()
    date_of_birth = serializers.DateField()
    verification_code = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

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
