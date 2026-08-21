from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.audit.services import log_action

from . import services
from .models import User
from .serializers import (
    ActivateSerializer,
    LoginSerializer,
    OfficerProfileSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    StudentProfileSerializer,
)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth-login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        ip_address = getattr(request, "audit_ip", None)

        if services.is_locked_out(email, ip_address):
            return Response(
                {"detail": "Too many failed attempts. Please try again later or reset your password."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        user = authenticate(request, username=email, password=password)
        if user is None:
            services.record_failed_login(email, ip_address, request=request)
            return Response({"detail": "Incorrect email or password."}, status=status.HTTP_401_UNAUTHORIZED)

        login(request, user)
        services.record_successful_login(user, request=request)
        return Response({"user_type": user.user_type, "email": user.email, "must_change_password": user.must_change_password})


class LogoutView(APIView):
    def post(self, request):
        log_action(AuditLog.Action.LOGOUT, actor=request.user, request=request)
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ActivateView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth-activate"

    def post(self, request):
        serializer = ActivateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = services.activate_student_account(request=request, **serializer.validated_data)
        except services.ActivationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        login(request, user)
        return Response({"user_type": user.user_type, "email": user.email}, status=status.HTTP_201_CREATED)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth-password-reset"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        # Always return 202 regardless of whether the account exists, so this
        # endpoint cannot be used to enumerate registered email addresses.
        if user is not None:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = f"{settings.PORTAL_BASE_URL}/reset-password?uid={uid}&token={token}"
            send_mail(
                "Reset your Scholarship Portal password",
                f"Use this link to reset your password: {reset_link}\nIf you did not request this, ignore this email.",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
            log_action(AuditLog.Action.PASSWORD_RESET_REQUESTED, actor=user, request=request)
        return Response(status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            uid = force_str(urlsafe_base64_decode(data["uid"]))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, data["token"]):
            return Response({"detail": "Invalid or expired reset link."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(data["new_password"])
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])
        log_action(AuditLog.Action.PASSWORD_RESET_COMPLETED, actor=user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.user_type == User.UserType.STUDENT:
            return Response(StudentProfileSerializer(user.student_profile).data)
        return Response(OfficerProfileSerializer(user.officer_profile).data)
